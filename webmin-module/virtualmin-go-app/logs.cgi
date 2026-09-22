#!/usr/bin/perl
# virtualmin-go-app logs.cgi — per-domain service log viewer (read-only).
use strict;
use warnings;
our (%in, %text);
do 'virtualmin-go-app-lib.pl';
&ReadParse();

my @instances = &vgo_visible_instances();
&error('No Go instances are visible to your login.') if !@instances;
my $domain = lc($in{'domain'} || $instances[0]->{'DOMAIN'});
my $inst = &vgo_assert_visible($domain);
my $lines = $in{'lines'} || 200;
$lines = 200 if $lines !~ /^\d+$/;
$lines = 20 if $lines < 20;
$lines = vgo_max_log_lines() if $lines > vgo_max_log_lines();

my ($rc, $out) = vgo_run_opts({ timeout => 30 }, 'logs', '--domain', $domain, '--lines', $lines);
&ui_print_header(undef, "Go Logs: $domain", '', 'go');
my $opts = join('', map {
    my $d = $_->{'DOMAIN'};
    "<option value='".vgo_html($d)."'".($d eq $domain ? ' selected' : '').">".vgo_html($d)."</option>";
} @instances);
print &ui_form_start('logs.cgi', 'get');
print "Domain: <select name='domain' onchange='this.form.submit()'>$opts</select> ";
print &ui_table_row('Lines', &ui_textbox('lines', $lines, 8)." (20 to ".vgo_max_log_lines().")");
print &ui_form_end([['show', 'Show logs']]);
print "<pre>".vgo_html($out || 'No matching log lines were returned.')."</pre>\n";
print "<p><a href='status.cgi?domain=".vgo_url($domain)."'>Status</a> | <a href='index.cgi'>All instances</a></p>\n";
&ui_print_footer('index.cgi', 'Go Applications');
