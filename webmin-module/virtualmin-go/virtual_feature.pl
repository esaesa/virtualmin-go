# Virtualmin Go - Webmin/Virtualmin Go instance manager
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
use strict;
use warnings;
our (%text, %config, $module_name);
do 'virtualmin-go-lib.pl';

my $cli = $config{'cli'} || '/usr/local/sbin/virtualmin-go';

# ── Core ─────────────────────────────────────────────────────────────

sub feature_name
{
return $text{'feat_name'};
}

sub feature_label
{
my ($edit) = @_;
return $edit ? $text{'feat_label2'} : $text{'feat_label'};
}

sub feature_hlink
{
my ($edit) = @_;
return "feature";
}

sub feature_check
{
if (!-x $cli) {
	return &text('feat_check_cli', "<tt>$cli</tt>");
	}
if (!-x '/bin/systemctl' && !-x '/usr/bin/systemctl') {
	return $text{'feat_check_systemd'};
	}
if (!-x '/usr/sbin/apachectl' && !-x '/usr/bin/apachectl') {
	return $text{'feat_check_apache'};
	}
return undef;
}

# ── Feature lifecycle ────────────────────────────────────────────────

sub feature_depends
{
my ($d) = @_;
if ($d->{'web'}) {
	return undef;
	}
else {
	return $text{'feat_edepweb'};
	}
}

sub feature_suitable
{
my ($parent, $alias, $super) = @_;
if ($parent && !$parent->{'dom'}) {
	return 0;
	}
if ($parent && !$parent->{'user'}) {
	return 0;
	}
if ($parent && !$parent->{'home'}) {
	return 0;
	}
return 1;
}

# Non-destructive setup: creates apps/go tree, reserves a port, registers.
# Never proxies / until a valid release is deployed.
sub feature_setup
{
my ($d) = @_;
&virtual_server::obtain_lock_web($d);
&$virtual_server::first_print(&text('feat_setup', $d->{'dom'}));
my $registry = "/etc/virtualmin-go/instances.d/".$d->{'dom'}.".conf";
my ($rc, $out);
if (-f $registry) {
	($rc, $out) = &vgo_run('enable', '--domain', $d->{'dom'});
	}
else {
	($rc, $out) = &vgo_run('enable', '--domain', $d->{'dom'});
	}
if ($rc != 0) {
	&$virtual_server::second_print(".. failed: ".$out);
	&virtual_server::release_lock_web($d);
	return 0;
	}
&$virtual_server::second_print($text{'feat_setup_done'});
&virtual_server::release_lock_web($d);
return 1;
}

sub feature_delete
{
my ($d) = @_;
&virtual_server::obtain_lock_web($d);
&$virtual_server::first_print(&text('feat_delete', $d->{'dom'}));
my ($rc, $out) = &vgo_run('remove', '--domain', $d->{'dom'}, '--keep-data');
if ($rc != 0) {
	&$virtual_server::second_print(".. failed: ".$out);
	&virtual_server::release_lock_web($d);
	return 0;
	}
&$virtual_server::second_print($text{'feat_setup_done'});
&virtual_server::release_lock_web($d);
return 1;
}

sub feature_disable
{
my ($d) = @_;
&$virtual_server::first_print(&text('feat_disable', $d->{'dom'}));
my ($rc, $out) = &vgo_run('disable', '--domain', $d->{'dom'});
if ($rc != 0) {
	&$virtual_server::second_print(".. failed: ".$out);
	return 0;
	}
&$virtual_server::second_print($text{'feat_setup_done'});
return 1;
}

sub feature_enable
{
my ($d) = @_;
&$virtual_server::first_print(&text('feat_enable', $d->{'dom'}));
my ($rc, $out) = &vgo_run('enable', '--domain', $d->{'dom'});
if ($rc != 0) {
	&$virtual_server::second_print(".. failed: ".$out);
	return 0;
	}
&$virtual_server::second_print($text{'feat_setup_done'});
return 1;
}

sub feature_modify
{
my ($d, $oldd) = @_;
if ($d->{'dom'} ne $oldd->{'dom'} ||
    $d->{'user'} ne $oldd->{'user'} ||
    $d->{'home'} ne $oldd->{'home'}) {
	&$virtual_server::first_print($text{'feat_modify_warn'});
	&$virtual_server::second_print($text{'feat_modify_warn2'});
	}
return undef;
}

sub feature_validate
{
my ($d) = @_;
my ($rc, $out) = &vgo_run('validate', '--domain', $d->{'dom'});
return ($rc == 0) ? undef : $out;
}

# ── Lifecycle descriptions ───────────────────────────────────────────

sub feature_losing
{
my ($d) = @_;
return $text{'feat_losing'}." at ".
       $d->{'home'}."/apps/go";
}

sub feature_disname
{
return $text{'feat_disname'};
}

sub feature_clash
{
my ($d) = @_;
my $registry = "/etc/virtualmin-go/instances.d/".$d->{'dom'}.".conf";
if (-f $registry) {
	return $text{'feat_clash'};
	}
return undef;
}

sub feature_import
{
my ($dname, $user, $db) = @_;
my $registry = "/etc/virtualmin-go/instances.d/".$dname.".conf";
if (-f $registry) {
	return 1;
	}
# Canonical path uses the Virtualmin server home (correct for subservers).
my $home = undef;
eval {
	my $d = &virtual_server::get_domain_by("dom", $dname);
	$home = $d->{'home'} if ($d && $d->{'home'});
	};
if ($home && -d "$home/apps/go" && -f "$home/apps/go/.virtualmin-go.env") {
	return 1;
	}
return 0;
}

sub feature_bandwidth
{
my ($d, $start, $bwhash) = @_;
return 0;
}

# ── Dashboard ────────────────────────────────────────────────────────

sub theme_sections
{
my $instances_dir = "/etc/virtualmin-go/instances.d";
my @instances;
if (-d $instances_dir) {
	for my $file (glob("$instances_dir/*.conf")) {
		next unless -f $file;
		my ($domain) = ($file =~ m{/([^/]+)\.conf$});
		push(@instances, $domain) if $domain;
		}
	}
my $count = scalar(@instances);
my $s = $count != 1 ? 's' : '';
my $html = "<p><b>$count</b> Go application$s configured. Ports 18100-18199.</p>\n";
if ($count > 0) {
	$html .= "<table class='ui_table'>\n";
	$html .= "<tr><th>Domain</th><th>Version</th><th>Port</th><th>State</th></tr>\n";
	for my $dom (@instances) {
		my $inst = &vgo_load_instance($dom);
		my $ver = ($inst && $inst->{'CURRENT_VERSION'}) ? $inst->{'CURRENT_VERSION'} : '(none)';
		my $port = ($inst && $inst->{'PORT'}) ? $inst->{'PORT'} : '';
		# Live state only: cheap local systemd check, no HTTP, no CLI spawn
		# (mirrors PocketBase dashboard practice of registry-first rendering).
		my $state = 'configured';
		if ($inst && $inst->{'SERVICE_NAME'}) {
			my $svc = $inst->{'SERVICE_NAME'};
			$svc =~ s/[^A-Za-z0-9_@.:-]/_/g;
			$state = (system("systemctl is-active --quiet ".quotemeta($svc)." 2>/dev/null") == 0)
				? 'running' : ($inst->{'ENTRYPOINT'} ? 'deployed' : 'configured');
			$state = 'disabled' if ($inst->{'ENABLED'} || '1') eq '0';
			}
		$html .= "<tr><td><a href='virtualmin-go/status.cgi?domain=".
			  &urlize($dom)."'>".&html_escape($dom)."</a></td>".
			  "<td>".&html_escape($ver)."</td>".
			  "<td>".&html_escape($port)."</td>".
			  "<td>$state</td></tr>\n";
		}
	$html .= "</table>\n";
	}
return ( { 'title' => $text{'theme_title'},
	   'html' => $html,
	   'status' => 1,
	   'for_master' => 1 } );
}

# ── Links & ACL ──────────────────────────────────────────────────────

sub feature_links
{
my ($d) = @_;
my @links;
push(@links, { 'mod' => $module_name,
	       'desc' => 'Go Status',
	       'page' => 'status.cgi?dom='.$d->{'id'},
	       'cat' => 'services',
	 });
push(@links, { 'mod' => $module_name,
	       'desc' => 'Go Validate',
	       'page' => 'validate.cgi?dom='.$d->{'id'},
	       'cat' => 'services',
	 });
return @links;
}

sub feature_always_links
{
	return ( );
}

sub feature_webmin
{
my ($d, $all) = @_;
my @fdoms = map { $_->{'dom'} } grep { $_->{$module_name} } @$all;
if (@fdoms) {
	return ( [ $module_name, { 'doms' => join(" ", @fdoms) } ] );
	}
else {
	return ( );
	}
}

sub feature_modules
{
return ( [ $module_name, $text{'feat_module'} ] );
}

# ── Backup & restore ─────────────────────────────────────────────────

sub feature_backup
{
my ($d, $file, $opts, $allopts) = @_;
my ($rc, $out) = &vgo_run('backup', '--domain', $d->{'dom'}, '--dest', $file);
return ($rc == 0) ? undef : $out;
}

sub feature_restore
{
my ($d, $file, $opts, $allopts) = @_;
my ($rc, $out) = &vgo_run('restore', '--domain', $d->{'dom'}, '--source', $file);
return ($rc == 0) ? undef : $out;
}

sub feature_backup_name
{
return $text{'feat_backup_name'};
}

# ── Settings link ────────────────────────────────────────────────────

sub settings_links
{
return ( { 'link' => "/$module_name/edit_config.cgi",
	   'title' => $text{'settings_title'},
	   'cat' => 'setting' } );
}

1;
