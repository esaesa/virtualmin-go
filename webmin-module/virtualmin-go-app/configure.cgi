#!/usr/bin/perl
# virtualmin-go-app configure.cgi — per-instance safe settings (pin, paths,
# port) + post-change validation. Mirrors PB configure.cgi shape.
# Never touches secrets, releases, or other plugins' config.
use strict;
use warnings;
our (%in, %text);
do 'virtualmin-go-app-lib.pl';
&ReadParse();

my $domain = &vgo_request_domain();
&error('No valid domain was specified.') if !$domain;
my $inst = &vgo_assert_visible($domain);

my ($message, $type, $details) = ('', 'info', '');
if (uc($ENV{'REQUEST_METHOD'} || 'GET') eq 'POST' && $in{'save'}) {
    &vgo_require_write('instance reconfiguration');
    &error('Domain confirmation did not match.') if ($in{'confirm_domain'} || '') ne $domain;
    my $wants_port = $in{'wants_port'} ? 1 : 0;
    my $newver = $in{'toolchain'} || '';
    my $health = $in{'health_path'} || '/health';
    my $ready = $in{'ready_path'} || '/ready';
    &error('Health path must start with /.') if $health !~ m{^/};
    &error('Ready path must start with /.') if $ready !~ m{^/};
    if ($newver ne '' && lc($newver) ne 'default') {
        &error('Invalid toolchain version.') if $newver !~ /^(go)?1\.[0-9]+(\.[0-9]+)?$/;
        my ($rc, $out) = vgo_run('pin-toolchain', '--domain', $domain, '--version', $newver);
        $details .= $out;
        &error("Toolchain pin failed: $out") if $rc != 0;
    }
    elsif (lc($newver) eq 'default' && ($inst->{'GO_TOOLCHAIN'} || '') ne '') {
        my ($rc, $out) = vgo_run('pin-toolchain', '--domain', $domain, '--follow-default');
        $details .= $out;
        &error("Unpin failed: $out") if $rc != 0;
    }
    # Health/ready paths are registry+metadata only (status checks + future
    # deploys); no service restart needed.
    &error('Health/ready paths may only contain URL-safe characters.')
        if $health !~ m{^/[A-Za-z0-9_./-]*$} || $ready !~ m{^/[A-Za-z0-9_./-]*$};
    if ($health ne ($inst->{'HEALTH_PATH'} || '/health') || $ready ne ($inst->{'READY_PATH'} || '/ready')) {
        my $reg = $inst->{'_REGISTRY_FILE'};
        open(my $fh, '<', $reg) || &error("Cannot read registry: $!");
        my @lines = <$fh>;
        close($fh);
        for (@lines) {
            s/^HEALTH_PATH='.*'/HEALTH_PATH='$health'/ if /^HEALTH_PATH=/;
            s/^READY_PATH='.*'/READY_PATH='$ready'/ if /^READY_PATH=/;
        }
        my $tmp = "$reg.tmp.$$";
        open(my $out, '>', $tmp) || &error("Cannot write registry: $!");
        print $out @lines;
        close($out) || &error("Cannot close registry: $!");
        chmod(0640, $tmp);
        rename($tmp, $reg) || &error("Cannot publish registry: $!");
        vgo_audit(action => 'configure-paths', domain => $domain, rc => 0, result => 'success');
    }
    if ($wants_port) {
        my $port = $in{'port'} || '';
        &error('Port must be 18100-18199.') if $port !~ /^\d+$/ || $port < 18100 || $port > 18199;
        my ($rc, $out) = vgo_run_opts({ timeout => 300 }, 'reassign-port', '--domain', $domain, '--port', $port);
        $details .= "\n$out";
        &error("Port reassignment failed: $out") if $rc != 0;
    }
    $inst = vgo_load_instance($domain) || $inst;
    my ($vrc, $vout) = vgo_run_opts({ timeout => 120, audit_read => 1 }, 'validate', '--domain', $domain);
    $details .= "\n\nPost-change validation:\n$vout";
    if ($vrc != 0) {
        $message = 'Configuration saved, but post-change validation reported a problem.';
        $type = 'warn';
    }
    else {
        $message = 'Go configuration updated successfully.';
        $type = 'good';
    }
}

&ui_print_header(undef, "Configure Go: $domain", '', 'go');
if ($message) {
    print "<p><b>".vgo_html($message)."</b></p>\n";
    print "<pre>".vgo_html($details)."</pre>\n" if $details;
}
my ($rc, $out) = vgo_run_opts({ timeout => 30 }, 'list-toolchains', '--json');
my $tcdata = vgo_json_from_output($out) || {};
my @tcs = ref($tcdata->{'toolchains'}) eq 'ARRAY' ? @{$tcdata->{'toolchains'}} : ();
my $cur_pin = $inst->{'GO_TOOLCHAIN'} || 'default';
my $tcopts = "<option value='default'".($cur_pin eq 'default' || $cur_pin eq '' ? ' selected' : '').">default (follow global)</option>";
for my $t (@tcs) {
    my $v = $t->{'version'};
    $tcopts .= "<option value='".vgo_html($v)."'".($v eq $cur_pin ? ' selected' : '').">".vgo_html($v)."</option>";
}
print &ui_form_start('configure.cgi', 'post');
print &ui_table_start('Instance settings', 'width=100%', 2);
print &ui_table_row('Toolchain pin', "<select name='toolchain'>$tcopts</select>");
print &ui_table_row('Health path', &ui_textbox('health_path', $inst->{'HEALTH_PATH'} || '/health', 20));
print &ui_table_row('Ready path', &ui_textbox('ready_path', $inst->{'READY_PATH'} || '/ready', 20));
print &ui_table_row('Reassign port',
    "<label><input type='checkbox' name='wants_port' value='1'> change to</label> ".
    &ui_textbox('port', $inst->{'PORT'} || '', 8)." (18100-18199)");
print &ui_table_row('Confirm domain', &ui_textbox('confirm_domain', '', 30)." (retype <tt>".vgo_html($domain)."</tt>)");
print &ui_table_end();
print "<input type='hidden' name='domain' value='".vgo_html($domain)."'>";
print &ui_form_end([['save', 'Save configuration']]);
print "<p>Mode, source, and releases are set at deploy time — see <a href='deploy.cgi?domain=".vgo_url($domain)."'>Deploy</a> and <a href='releases.cgi?domain=".vgo_url($domain)."'>Releases</a>.</p>\n";
print "<p><a href='status.cgi?domain=".vgo_url($domain)."'>Status</a> | <a href='index.cgi'>All instances</a></p>\n";
&ui_print_footer('index.cgi', 'Go Applications');
