#!/usr/bin/perl
# virtualmin-go edit_config.cgi — Global Settings (external manager config)
# Mirrors virtualmin-pocketbase/edit_config.cgi: validated inputs, atomic
# publish with backup, audit trail. Never touches instance secrets.
use strict;
use warnings;
our (%in, %config, %text, $CONFIG_FILE);
do 'virtualmin-go-lib.pl';
&ReadParse();

my $cfg = vgo_global_config();
my @keys = qw(GO_BASE_PORT GO_MAX_PORT GO_LISTEN_HOST GO_APP_SUBDIR
    GO_DEFAULT_PROXY_PATH GO_DEFAULT_HEALTH_PATH GO_DEFAULT_READY_PATH
    GO_HEALTH_TIMEOUT GO_HEALTH_RETRIES GO_KEEP_RELEASES
    GO_DEFAULT_LIMIT_NOFILE GO_RESTART_POLICY GO_RESTART_SEC GO_APACHE_TIMEOUT);
my ($message, $type) = ('', 'info');

if (uc($ENV{'REQUEST_METHOD'} || 'GET') eq 'POST' && $in{'save'}) {
    &vgo_require_write('global configuration update');
    my %new = %$cfg;
    my $base = $in{'GO_BASE_PORT'} || '';
    my $max = $in{'GO_MAX_PORT'} || '';
    &error('Base port must be between 1024 and 65534.') if $base !~ /^\d+$/ || $base < 1024 || $base > 65534;
    &error('Maximum port must be >= base port and at most 65535.') if $max !~ /^\d+$/ || $max < $base || $max > 65535;
    &error('Go range must not overlap PocketBase 18000-18999.') if !($max < 18000 || $base > 18999);
    my $listen = $in{'GO_LISTEN_HOST'} || '127.0.0.1';
    &error('Listen host must remain loopback-only.') if $listen !~ /^(?:127\.0\.0\.1|localhost|::1)$/;
    my $app = $in{'GO_APP_SUBDIR'} || 'apps/go';
    &error('App subdirectory must be a relative safe path.') if $app !~ m{^[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*$} || $app =~ /\.\./;
    my $proxy = $in{'GO_DEFAULT_PROXY_PATH'} || '/';
    &error('V1 supports only proxy path /.') if $proxy ne '/';
    for my $hp (qw(GO_DEFAULT_HEALTH_PATH GO_DEFAULT_READY_PATH)) {
        my $v = $in{$hp} || ($hp eq 'GO_DEFAULT_HEALTH_PATH' ? '/health' : '/ready');
        &error("$hp must start with /.") if $v !~ m{^/};
        $new{$hp} = $v;
    }
    for my $num (qw(GO_HEALTH_TIMEOUT GO_HEALTH_RETRIES GO_KEEP_RELEASES GO_RESTART_SEC GO_APACHE_TIMEOUT)) {
        my $v = $in{$num} || '';
        &error("$num must be a positive number.") if $v !~ /^\d+$/ || $v < 1;
        $new{$num} = $v;
    }
    my $keep = $new{'GO_KEEP_RELEASES'};
    &error('Release retention must be at least 2 (protects current+previous).') if $keep < 2;
    my $nofile = $in{'GO_DEFAULT_LIMIT_NOFILE'} || '65535';
    &error('NOFILE limit must be between 256 and 1048576.') if $nofile !~ /^\d+$/ || $nofile < 256 || $nofile > 1048576;
    my $pol = $in{'GO_RESTART_POLICY'} || 'on-failure';
    &error('Restart policy must be on-failure, always, or no.') if $pol !~ /^(?:on-failure|always|no)$/;
    $new{'GO_BASE_PORT'} = $base;
    $new{'GO_MAX_PORT'} = $max;
    $new{'GO_LISTEN_HOST'} = $listen;
    $new{'GO_APP_SUBDIR'} = $app;
    $new{'GO_DEFAULT_PROXY_PATH'} = $proxy;
    $new{'GO_DEFAULT_LIMIT_NOFILE'} = $nofile;
    $new{'GO_RESTART_POLICY'} = $pol;

    my ($ok, $err) = vgo_ensure_dir(dirname($CONFIG_FILE), 0750);
    &error($err) if !$ok;
    my $backup_dir = vgo_backup_dir().'/config-history';
    ($ok, $err) = vgo_ensure_dir($backup_dir, 0700);
    &error($err) if !$ok;
    my $backup = '';
    if (-f $CONFIG_FILE) {
        $backup = "$backup_dir/config-".vgo_stamp();
        open(my $src, '<', $CONFIG_FILE) || &error("Cannot read current config: $!");
        open(my $dst, '>', $backup) || &error("Cannot create config backup: $!");
        while (my $buf = <$src>) { print $dst $buf; }
        close($src); close($dst); chmod(0600, $backup);
    }
    my $tmp = "$CONFIG_FILE.tmp.$$";
    open(my $fh, '>', $tmp) || &error("Cannot write temporary config: $!");
    print $fh "# virtualmin-go global config\n# Updated ".vgo_now_iso()." through Webmin\n\n";
    my %printed;
    for my $key (@keys) {
        if (exists($new{$key})) {
            my $value = $new{$key};
            $value =~ s/[\r\n]//g;
            print $fh "$key=$value\n";
            $printed{$key} = 1;
        }
    }
    for my $key (sort keys %new) {
        next if $printed{$key};
        next if $key !~ /^[A-Z][A-Z0-9_]*$/;
        my $value = $new{$key};
        next if !defined($value) || ref($value);
        $value =~ s/[\r\n]//g;
        print $fh "$key=$value\n";
    }
    close($fh) || &error("Cannot close temporary config: $!");
    chmod(0640, $tmp);
    rename($tmp, $CONFIG_FILE) || &error("Cannot atomically publish configuration: $!");
    vgo_audit(action => 'save-global-config', domain => '', command => 'atomic config update',
              rc => 0, result => 'success', backup => $backup);
    $cfg = vgo_global_config();
    $message = $backup ? "Configuration saved. Previous file: $backup" : 'Configuration saved.';
    $type = 'good';
}

&ui_print_header(undef, 'Go Global Settings', '', 'config');
if ($message) {
    print "<p><b>".vgo_html($message)."</b></p>\n";
}
print "<p>Validate and atomically update the external manager configuration. Existing configuration is backed up before replacement. Applies to new enables/deploys; running instances keep their reserved ports.</p>\n";
print "<p><b>Production guardrails:</b> listener stays loopback-only, Go range must not overlap PocketBase 18000-18999, retention keeps current+previous.</p>\n";
print &ui_form_start('edit_config.cgi', 'post');
print &ui_table_start('Global settings', 'width=100%', 2);
print &ui_table_row('Base port',
    &ui_textbox('GO_BASE_PORT', $cfg->{'GO_BASE_PORT'} || 18100, 10));
print &ui_table_row('Maximum port',
    &ui_textbox('GO_MAX_PORT', $cfg->{'GO_MAX_PORT'} || 18199, 10));
print &ui_table_row('Listen host',
    &ui_textbox('GO_LISTEN_HOST', $cfg->{'GO_LISTEN_HOST'} || '127.0.0.1', 20));
print &ui_table_row('App subdirectory',
    &ui_textbox('GO_APP_SUBDIR', $cfg->{'GO_APP_SUBDIR'} || 'apps/go', 20));
print &ui_table_row('Default proxy path',
    &ui_textbox('GO_DEFAULT_PROXY_PATH', $cfg->{'GO_DEFAULT_PROXY_PATH'} || '/', 10));
print &ui_table_row('Default health path',
    &ui_textbox('GO_DEFAULT_HEALTH_PATH', $cfg->{'GO_DEFAULT_HEALTH_PATH'} || '/health', 20));
print &ui_table_row('Default ready path',
    &ui_textbox('GO_DEFAULT_READY_PATH', $cfg->{'GO_DEFAULT_READY_PATH'} || '/ready', 20));
print &ui_table_row('Health timeout (s)',
    &ui_textbox('GO_HEALTH_TIMEOUT', $cfg->{'GO_HEALTH_TIMEOUT'} || 15, 10));
print &ui_table_row('Health retries',
    &ui_textbox('GO_HEALTH_RETRIES', $cfg->{'GO_HEALTH_RETRIES'} || 10, 10));
print &ui_table_row('Release retention',
    &ui_textbox('GO_KEEP_RELEASES', $cfg->{'GO_KEEP_RELEASES'} || 5, 10));
print &ui_table_row('Default NOFILE limit',
    &ui_textbox('GO_DEFAULT_LIMIT_NOFILE', $cfg->{'GO_DEFAULT_LIMIT_NOFILE'} || 65535, 10));
print &ui_table_row('Restart policy',
    &ui_select('GO_RESTART_POLICY', $cfg->{'GO_RESTART_POLICY'} || 'on-failure',
        [['on-failure', 'on-failure'], ['always', 'always'], ['no', 'no']]));
print &ui_table_row('Restart delay (s)',
    &ui_textbox('GO_RESTART_SEC', $cfg->{'GO_RESTART_SEC'} || 2, 10));
print &ui_table_row('Apache proxy timeout (s)',
    &ui_textbox('GO_APACHE_TIMEOUT', $cfg->{'GO_APACHE_TIMEOUT'} || 60, 10));
print &ui_table_end();
print &ui_form_end([['save', 'Save settings']]);
&ui_print_footer('index.cgi', 'Go Applications');
