#!/usr/bin/perl
# virtualmin-go-app toolchains.cgi — shared Go toolchain store management
# Mirrors virtualmin-pocketbase/binaries.cgi. Global install/set-current/
# remove are master-only; per-instance pins respect owner visibility.
use strict;
use warnings;
our (%in, %config, %text);
do 'virtualmin-go-app-lib.pl';
&ReadParse();

my ($message, $type, $details) = ('', 'info', '');
my $method = uc($ENV{'REQUEST_METHOD'} || 'GET');

if ($method eq 'POST' && $in{'operation'}) {
    &vgo_require_write('toolchain operation');
    my $op = $in{'operation'};
    if ($op eq 'check') {
        my ($rc, $out) = vgo_run_opts({ audit_read => 1, timeout => 60 }, 'check-updates');
        $message = $rc == 0 ? 'Update check completed.' : 'Update check failed.';
        $type = $rc == 0 ? 'good' : 'bad';
        $details = $out;
    }
    elsif ($op eq 'install') {
        &vgo_require_master('toolchain install');
        my $version = $in{'version'} || '';
        &error('Enter a version like 1.23.0 or latest.') if $version ne 'latest' && $version !~ /^(go)?1\.[0-9]+(\.[0-9]+)?$/;
        &error('Confirmation must match the requested version.') if ($in{'confirm_value'} || '') ne $version;
        my @args = ('install-toolchain', $version eq 'latest' ? '--latest' : ('--version', $version));
        push(@args, '--set-current') if $in{'set_current'};
        push(@args, '--allow-online') if $in{'allow_online'};
        my ($rc, $out) = vgo_run_opts({ timeout => 900 }, @args);
        $message = $rc == 0 ? 'Toolchain install completed.' : 'Toolchain install failed.';
        $type = $rc == 0 ? 'good' : 'bad';
        $details = $out;
    }
    elsif ($op eq 'set-current') {
        &vgo_require_master('default toolchain change');
        my $version = $in{'version'} || '';
        &error('Invalid version.') if $version !~ /^(go)?1\.[0-9]+(\.[0-9]+)?$/;
        &error('Confirmation must match the version.') if ($in{'confirm_value'} || '') ne $version;
        my ($rc, $out) = vgo_run('set-current-toolchain', '--version', $version);
        $message = $rc == 0 ? "Go $version is now the default toolchain." : 'Default change failed.';
        $type = $rc == 0 ? 'good' : 'bad';
        $details = $out;
    }
    elsif ($op eq 'pin') {
        my $domain = lc($in{'domain'} || '');
        my $inst = &vgo_assert_visible($domain);
        my $version = $in{'version'} || '';
        if ($version eq '' || lc($version) eq 'default') {
            my ($rc, $out) = vgo_run('pin-toolchain', '--domain', $domain, '--follow-default');
            $message = $rc == 0 ? "$domain now follows the default toolchain." : 'Unpin failed.';
            $type = $rc == 0 ? 'good' : 'bad';
            $details = $out;
        }
        else {
            &error('Invalid version.') if $version !~ /^(go)?1\.[0-9]+(\.[0-9]+)?$/;
            &error('Confirmation must match the domain.') if ($in{'confirm_value'} || '') ne $domain;
            my ($rc, $out) = vgo_run('pin-toolchain', '--domain', $domain, '--version', $version);
            $message = $rc == 0 ? "$domain pinned to Go $version." : 'Pin failed.';
            $type = $rc == 0 ? 'good' : 'bad';
            $details = $out;
        }
    }
    elsif ($op eq 'remove') {
        &vgo_require_master('toolchain removal');
        my $version = $in{'version'} || '';
        &error('Invalid version.') if $version !~ /^(go)?1\.[0-9]+(\.[0-9]+)?$/;
        &error('Confirmation must match the version.') if ($in{'confirm_value'} || '') ne $version;
        my ($rc, $out) = vgo_run('remove-toolchain', '--version', $version);
        $message = $rc == 0 ? "Go $version removed." : 'Removal failed (pinned or current?).';
        $type = $rc == 0 ? 'good' : 'bad';
        $details = $out;
    }
    else {
        &error('Unknown toolchain operation.');
    }
}

&ui_print_header(undef, 'Go Toolchains', '', 'go');
if ($message) {
    print "<p><b>".vgo_html($message)."</b></p>\n";
    print "<pre>".vgo_html($details || '')."</pre>\n" if $details;
}
my ($rc, $out) = vgo_run_opts({ timeout => 30 }, 'list-toolchains', '--json');
my $data = vgo_json_from_output($out) || {};
my $current = $data->{'current'} || '';
my @tcs = ref($data->{'toolchains'}) eq 'ARRAY' ? @{$data->{'toolchains'}} : ();
print "<p>Shared compilers in <tt>/opt/virtualmin-go-app/toolchains</tt>. Default: <b>".vgo_html($current || '(none)')."</b>. Application binaries stay per-instance under <tt>apps/go</tt>.</p>\n";
if (@tcs) {
    print "<table class='ui_table' width='100%'>\n";
    print "<tr><th>Version</th><th>Pinned by</th><th>Actions</th></tr>\n";
    for my $t (@tcs) {
        my $v = $t->{'version'};
        my $mark = ($v eq $current) ? ' (default)' : '';
        print "<tr><td>".vgo_html($v).vgo_html($mark)."</td>";
        print "<td>".vgo_html($t->{'pinned_by'} || '-')."</td>";
        print "<td><form method='post' action='toolchains.cgi' style='display:inline'>".
              "<input type='hidden' name='operation' value='set-current'>".
              "<input type='hidden' name='version' value='".vgo_html($v)."'>".
              "<input type='text' name='confirm_value' size='12' placeholder='type $v to confirm'>".
              "<input type='submit' value='Set default'></form></td></tr>\n";
    }
    print "</table>\n";
}
else {
    print "<p>No toolchains installed yet.</p>\n";
}
print "<h3>Install a toolchain</h3>\n";
print &ui_form_start('toolchains.cgi', 'post');
print &ui_table_start('Install', 'width=100%', 2);
print &ui_table_row('Version', &ui_textbox('version', '', 16)." (e.g. 1.23.0, or <tt>latest</tt>)");
print &ui_table_row('Confirm', &ui_textbox('confirm_value', '', 16)." (retype the version)");
print &ui_table_row('Options',
    "<label><input type='checkbox' name='set_current' value='1'> Set as default</label><br>".
    "<label><input type='checkbox' name='allow_online' value='1'> Allow online download</label>");
print &ui_table_end();
print "<input type='hidden' name='operation' value='install'>";
print &ui_form_end([['install', 'Install toolchain']]);
my @instances = &vgo_visible_instances();
if (@instances) {
    print "<h3>Pin an instance</h3>\n";
    print &ui_form_start('toolchains.cgi', 'post');
    my $opts = join('', map {
        "<option value='".vgo_html($_->{'DOMAIN'})."'>".vgo_html($_->{'DOMAIN'})."</option>";
    } @instances);
    print &ui_table_start('Pin', 'width=100%', 2);
    print &ui_table_row('Domain', "<select name='domain'>$opts</select>");
    print &ui_table_row('Version', &ui_textbox('version', '', 16)." (empty/default = follow global default)");
    print &ui_table_row('Confirm', &ui_textbox('confirm_value', '', 30)." (domain name for pins)");
    print &ui_table_end();
    print "<input type='hidden' name='operation' value='pin'>";
    print &ui_form_end([['pin', 'Apply pin']]);
}
print "<p><a href='index.cgi'>All instances</a></p>\n";
&ui_print_footer('index.cgi', 'Go Applications');
