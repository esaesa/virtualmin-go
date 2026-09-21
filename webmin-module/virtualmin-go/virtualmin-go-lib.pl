#!/usr/bin/perl
# Virtualmin Go - shared safety, UI and operations library
# Copyright (C) 2026 Islam Sameh
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

=head1 NAME

virtualmin-go-lib.pl - shared safety, UI and operations library

=head1 DESCRIPTION

Keeps the Webmin module compatible with the external
C</usr/local/sbin/virtualmin-go> manager while ensuring that module
requests never construct shell command strings. Mutating commands are
serialized with locks and recorded in a private audit log. Secrets stored
in C<production.env> are never read or printed by this library.

=cut

BEGIN { push(@INC, '.'); push(@INC, '..'); }

use strict;
use warnings;
use WebminCore;
use Cwd qw(abs_path realpath);
use Digest::SHA qw(sha256_hex);
use Fcntl qw(:DEFAULT :flock);
use File::Basename qw(basename dirname);
use File::Path qw(make_path);
use IO::Select;
use IPC::Open3;
use JSON::PP qw(encode_json decode_json);
use POSIX qw(strftime);
use Symbol qw(gensym);
use Time::HiRes qw(time sleep);

our (%config, %text, %in, %access, $remote_user, $module_name);

&init_config();
eval { &foreign_require('virtual-server'); };
eval { %access = &get_module_acl(); };

our $SCRIPT_NAME = 'virtualmin-go';
our $CLI = $config{'cli'} || '/usr/local/sbin/virtualmin-go';
our $CONFIG_FILE = $ENV{'VGO_CONFIG_FILE'} || '/etc/virtualmin-go/config';
our $INSTANCES_DIR = $ENV{'VGO_INSTANCES_DIR'} || '/etc/virtualmin-go/instances.d';

sub vgo_version { return '0.1.1'; }
sub vgo_now_iso { return strftime('%Y-%m-%dT%H:%M:%S%z', localtime()); }
sub vgo_stamp { return strftime('%Y%m%d-%H%M%S', localtime()); }

sub vgo_html
{
    my ($s) = @_;
    $s = '' if !defined($s);
    $s =~ s/&/&amp;/g;
    $s =~ s/</&lt;/g;
    $s =~ s/>/&gt;/g;
    $s =~ s/"/&quot;/g;
    $s =~ s/'/&#39;/g;
    return $s;
}

sub vgo_url
{
    my ($s) = @_;
    $s = '' if !defined($s);
    $s =~ s/([^A-Za-z0-9_.~-])/sprintf('%%%02X', ord($1))/eg;
    return $s;
}

sub vgo_int_config
{
    my ($key, $default, $min, $max) = @_;
    my $value = exists($config{$key}) ? $config{$key} : $default;
    $value = $default if !defined($value) || $value !~ /^-?\d+$/;
    $value = int($value);
    $value = $min if defined($min) && $value < $min;
    $value = $max if defined($max) && $value > $max;
    return $value;
}

sub vgo_command_timeout { return vgo_int_config('command_timeout', 180, 5, 3600); }
sub vgo_max_output_bytes { return vgo_int_config('max_output_bytes', 2097152, 65536, 33554432); }
sub vgo_max_log_lines { return vgo_int_config('max_log_lines', 1000, 100, 5000); }
sub vgo_report_dir { return $config{'report_dir'} || '/root/service-reports/virtualmin-go'; }
sub vgo_backup_dir { return $config{'backup_dir'} || '/root/service-backups/virtualmin-go'; }
sub vgo_lock_dir { return $config{'lock_dir'} || '/run/lock/virtualmin-go-web'; }
sub vgo_audit_log { return $config{'audit_log'} || '/var/log/virtualmin-go/web-actions.log'; }

sub vgo_ensure_dir
{
    my ($dir, $mode) = @_;
    $mode ||= 0700;
    return (1, '') if -d $dir;
    eval { make_path($dir, { mode => $mode }); };
    return (0, $@ || "Unable to create $dir") if $@ || !-d $dir;
    chmod($mode, $dir);
    return (1, '');
}

sub vgo_valid_domain
{
    my ($domain) = @_;
    return 0 if !defined($domain);
    return 0 if length($domain) < 3 || length($domain) > 253;
    return 0 if $domain =~ /\.\./ || $domain =~ /[^A-Za-z0-9.-]/;
    return 0 if $domain !~ /^[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?$/;
    for my $label (split(/\./, $domain)) {
        return 0 if length($label) < 1 || length($label) > 63;
        return 0 if $label =~ /^-/ || $label =~ /-$/;
    }
    return 1;
}

sub vgo_require_post
{
    my ($label) = @_;
    $label ||= 'operation';
    &error("The $label must be submitted using POST.") if uc($ENV{'REQUEST_METHOD'} || 'GET') ne 'POST';
}

sub vgo_require_write
{
    my ($label) = @_;
    vgo_require_post($label);
    &error('This Webmin account has read-only Go access.') if $access{'readonly'};
}

sub vgo_request_domain
{
    my $domain = $in{'domain'} || '';
    if (!$domain && $in{'dom'} && defined(&virtual_server::get_domain)) {
        my $record = eval { &virtual_server::get_domain($in{'dom'}) };
        $domain = $record->{'dom'} if $record && $record->{'dom'};
    }
    $domain = lc($domain || '');
    return undef if !vgo_valid_domain($domain);
    return $domain;
}

sub vgo_decode_registry_value
{
    my ($value) = @_;
    $value = '' if !defined($value);
    $value =~ s/^\s+|\s+$//g;
    if ($value =~ /^'(.*)'$/s) {
        $value = $1;
        $value =~ s/'\\''/'/g;
    }
    elsif ($value =~ /^"(.*)"$/s) {
        $value = $1;
        $value =~ s/\\([\\"])/$1/g;
    }
    return $value;
}

sub vgo_load_instance
{
    my ($domain) = @_;
    return undef if !vgo_valid_domain($domain);
    my $file = "$INSTANCES_DIR/$domain.conf";
    return undef if !-f $file || -l $file;
    my %inst;
    open(my $fh, '<', $file) || return undef;
    while (my $line = <$fh>) {
        chomp($line);
        next if $line =~ /^\s*(?:#|$)/;
        if ($line =~ /^([A-Z][A-Z0-9_]*)=(.*)$/) {
            $inst{$1} = vgo_decode_registry_value($2);
        }
    }
    close($fh);
    return undef if !$inst{'DOMAIN'} || lc($inst{'DOMAIN'}) ne lc($domain);
    $inst{'_REGISTRY_FILE'} = $file;
    return \%inst;
}

sub vgo_list_instances
{
    my @instances;
    return @instances if !-d $INSTANCES_DIR;
    opendir(my $dh, $INSTANCES_DIR) || return @instances;
    for my $entry (sort readdir($dh)) {
        next if $entry !~ /^([A-Za-z0-9.-]+)\.conf$/;
        my $domain = lc($1);
        next if !vgo_valid_domain($domain);
        my $inst = vgo_load_instance($domain);
        push(@instances, $inst) if $inst;
    }
    closedir($dh);
    return @instances;
}

sub vgo_assert_instance
{
    my ($domain) = @_;
    &error('No valid domain was specified.') if !vgo_valid_domain($domain);
    my $inst = vgo_load_instance($domain);
    &error("No Go registry exists for $domain.") if !$inst;
    return $inst;
}

# Canonical app dir: HOME (SERVER_HOME) is authoritative. No /home/$USER guess.
sub vgo_app_dir
{
    my ($inst) = @_;
    return '' if !$inst;
    return $inst->{'APP_ROOT'} if $inst->{'APP_ROOT'} && $inst->{'APP_ROOT'} =~ m{^/};
    return '' if !$inst->{'HOME'};
    return "$inst->{'HOME'}/apps/go";
}

sub vgo_command_rules
{
    return {
        'status'         => 0,
        'validate'       => 0,
        'logs'           => 0,
        'releases'       => 0,
        'list'           => 0,
        'enable'         => 1,
        'disable'        => 1,
        'restart'        => 1,
        'rollback'       => 1,
        'prune-releases' => 1,
        'backup'         => 1,
        'restore'        => 1,
        'remove'         => 1,
    };
}

sub vgo_audit
{
    my (%event) = @_;
    my $file = vgo_audit_log();
    my $dir = dirname($file);
    my ($ok) = vgo_ensure_dir($dir, 0700);
    return if !$ok;
    sysopen(my $fh, $file, O_WRONLY|O_CREAT|O_APPEND, 0600) || return;
    flock($fh, LOCK_EX);
    chmod(0600, $file);
    my $line = encode_json({
        timestamp => vgo_now_iso(),
        user => ($ENV{'REMOTE_USER'} || $remote_user || 'unknown'),
        remote_addr => ($ENV{'REMOTE_ADDR'} || ''),
        %event,
    });
    print $fh $line."\n";
    close($fh);
}

sub vgo_operation_lock
{
    my ($scope) = @_;
    $scope ||= 'global';
    $scope =~ s/[^A-Za-z0-9_.-]/_/g;
    my $dir = vgo_lock_dir();
    my ($ok, $err) = vgo_ensure_dir($dir, 0700);
    return (undef, $err) if !$ok;
    my $file = "$dir/$scope.lock";
    sysopen(my $fh, $file, O_RDWR|O_CREAT, 0600) || return (undef, "Cannot open lock $file: $!");
    if (!flock($fh, LOCK_EX|LOCK_NB)) {
        close($fh);
        return (undef, "Another Go operation is already running for $scope.");
    }
    seek($fh, 0, 0);
    truncate($fh, 0);
    print $fh "pid=$$\nstarted=".vgo_now_iso()."\n";
    return ($fh, '');
}

sub vgo_extract_domain_arg
{
    my (@args) = @_;
    for (my $i = 0; $i < @args - 1; $i++) {
        return lc($args[$i+1]) if $args[$i] eq '--domain';
    }
    return '';
}

sub vgo_run
{
    my ($cmd, @args) = @_;
    return vgo_run_opts({}, $cmd, @args);
}

sub vgo_run_opts
{
    my ($opts, $cmd, @args) = @_;
    $opts ||= {};
    $cmd = 'enable' if defined($cmd) && $cmd eq 'start';
    $cmd = 'disable' if defined($cmd) && $cmd eq 'stop';
    my $rules = vgo_command_rules();
    return (64, 'Unsupported Go manager command.', { rejected => 1 }) if !$cmd || !exists($rules->{$cmd});
    return (69, "CLI manager $CLI is not installed or not executable.", { missing_cli => 1 }) if !-x $CLI || !-f $CLI;

    for my $arg (@args) {
        return (64, 'An invalid command argument was rejected.', { rejected => 1 })
            if !defined($arg) || ref($arg) || length($arg) > 4096 || $arg =~ /[\x00\r\n]/;
    }
    my $domain = vgo_extract_domain_arg(@args);
    return (64, 'Invalid domain argument.', { rejected => 1 }) if $domain && !vgo_valid_domain($domain);

    my $mutating = $rules->{$cmd} ? 1 : 0;
    my $lockfh;
    if ($mutating && !$opts->{'skip_lock'}) {
        my $scope = $domain || 'global';
        my ($fh, $lockerr) = vgo_operation_lock($scope);
        return (75, $lockerr, { locked => 1 }) if !$fh;
        $lockfh = $fh;
    }

    my $timeout = $opts->{'timeout'} || vgo_command_timeout();
    $timeout = 1 if $timeout < 1;
    my $max_bytes = $opts->{'max_output_bytes'} || vgo_max_output_bytes();
    my @argv = ($CLI, $cmd, @args);
    my $display = join(' ', map {
        my $s = $_;
        $s =~ s/'/'"'"'/g;
        "'$s'";
    } @argv);
    my $started = time();
    my ($pid, $spawn_error);
    my $child_in = gensym();
    my $child_out = gensym();
    my $child_err = gensym();

    local %ENV = (
        PATH => '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin',
        LANG => 'C', LC_ALL => 'C', HOME => '/root',
    );
    eval {
        $pid = open3($child_in, $child_out, $child_err, @argv);
        close($child_in);
        1;
    } or $spawn_error = $@ || 'Unable to start CLI manager.';

    if ($spawn_error) {
        my $duration = time() - $started;
        vgo_audit(action => $cmd, domain => $domain, command => $display, rc => 70,
                  duration_seconds => sprintf('%.3f', $duration), result => 'spawn-failed') if $mutating;
        close($lockfh) if $lockfh;
        return (70, $spawn_error, { command => $display, duration => $duration, spawn_failed => 1 });
    }

    my $selector = IO::Select->new($child_out, $child_err);
    my $output = '';
    my $timed_out = 0;
    my $truncated = 0;
    while ($selector->count()) {
        if ((time() - $started) > $timeout) {
            $timed_out = 1;
            last;
        }
        for my $fh ($selector->can_read(0.20)) {
            my $buffer = '';
            my $read = sysread($fh, $buffer, 16384);
            if (!defined($read) || $read == 0) {
                $selector->remove($fh);
                close($fh);
                next;
            }
            $output .= $buffer;
            if (length($output) > $max_bytes) {
                $output = substr($output, 0, $max_bytes);
                $output .= "\n[output truncated by Webmin module]\n";
                $truncated = 1;
                last;
            }
        }
        last if $truncated;
    }

    if ($timed_out || $truncated) {
        kill('TERM', $pid);
        sleep(0.25);
        kill('KILL', $pid) if kill(0, $pid);
    }
    waitpid($pid, 0);
    my $rc = $? == -1 ? 70 : ($? >> 8);
    $rc = 124 if $timed_out;
    $rc = 125 if $truncated && !$timed_out;
    my $duration = time() - $started;
    $output .= "\nCommand timed out after ${timeout}s.\n" if $timed_out;

    if ($mutating || $opts->{'audit_read'}) {
        vgo_audit(
            action => $cmd, domain => $domain, command => $display, rc => $rc,
            duration_seconds => sprintf('%.3f', $duration),
            result => ($rc == 0 ? 'success' : 'failed'),
            timed_out => ($timed_out ? JSON::PP::true : JSON::PP::false),
            truncated => ($truncated ? JSON::PP::true : JSON::PP::false),
        );
    }
    close($lockfh) if $lockfh;
    return ($rc, $output, {
        command => $display, duration => $duration, timed_out => $timed_out,
        truncated => $truncated, mutation => $mutating,
    });
}

sub vgo_json_from_output
{
    my ($out) = @_;
    return undef if !defined($out);
    my $candidate = $out;
    if ($candidate !~ /^\s*\{/s) {
        my $start = index($candidate, '{');
        my $end = rindex($candidate, '}');
        return undef if $start < 0 || $end <= $start;
        $candidate = substr($candidate, $start, $end - $start + 1);
    }
    my $data = eval { decode_json($candidate) };
    return ref($data) eq 'HASH' ? $data : undef;
}

sub vgo_status_snapshot
{
    my ($domain, $timeout) = @_;
    my ($rc, $out, $meta) = vgo_run_opts({ timeout => ($timeout || 15) }, 'status', '--domain', $domain, '--json');
    my $json = vgo_json_from_output($out) || {};
    my $status = lc($json->{'state'} || $json->{'status'} || '');
    if (!$status) {
        $status = 'running' if $out =~ /\b(?:active|running)\b/i && $out !~ /\binactive\b/i;
        $status = 'stopped' if $out =~ /\b(?:inactive|stopped|failed)\b/i;
    }
    $status ||= $rc == 0 ? 'unknown' : 'unavailable';
    return {
        rc => $rc, output => $out, meta => $meta, json => $json, status => $status,
    };
}

sub vgo_parse_checks
{
    my ($out) = @_;
    my @checks;
    for my $line (split(/\r?\n/, $out || '')) {
        if ($line =~ /^\s*(OK|PASS|WARN|WARNING|FAIL|ERROR)\s*[:\-]?\s*(.*)$/i) {
            my ($state, $message) = (uc($1), $2);
            $state = 'OK' if $state eq 'PASS';
            $state = 'WARN' if $state eq 'WARNING';
            $state = 'FAIL' if $state eq 'ERROR';
            push(@checks, { status => $state, message => $message });
        }
    }
    return @checks;
}

sub vgo_badge
{
    my ($label, $state) = @_;
    $state = lc($state || 'info');
    my $class = $state =~ /^(?:running|ok|pass|success|active|good|deployed)$/ ? 'good' :
                $state =~ /^(?:warn|warning|configured|disabled)$/ ? 'warn' :
                $state =~ /^(?:fail|failed|error|unavailable|bad|degraded)$/ ? 'bad' : 'info';
    return "<span class='vgo-badge vgo-$class'>".vgo_html($label).'</span>';
}

sub vgo_recent_audit
{
    my ($limit, $domain) = @_;
    $limit ||= 50;
    $limit = 500 if $limit > 500;
    my $file = vgo_audit_log();
    return () if !-f $file;
    open(my $fh, '<', $file) || return ();
    my @lines = <$fh>;
    close($fh);
    splice(@lines, 0, @lines - 3000) if @lines > 3000;
    my @events;
    for my $line (reverse @lines) {
        my $event = eval { decode_json($line) };
        next if ref($event) ne 'HASH';
        next if $domain && lc($event->{'domain'} || '') ne lc($domain);
        push(@events, $event);
        last if @events >= $limit;
    }
    return @events;
}

1;
