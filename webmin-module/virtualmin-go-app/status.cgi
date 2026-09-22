#!/usr/bin/perl
# virtualmin-go-app status.cgi — machine + human status for one domain
use strict;
use warnings;
our (%in, %text);
do 'virtualmin-go-app-lib.pl';
&ReadParse();

my $domain = &vgo_request_domain();
&error('No valid domain was specified.') if !$domain;
my $inst = &vgo_assert_visible($domain);

&ui_print_header(undef, "Go Status: $domain", '', 'go');

my ($rc, $out) = &vgo_run('status', '--domain', $domain);
print "<pre>".&html_escape($out)."</pre>\n";

my ($rcj, $outj) = &vgo_run_opts({ timeout => 15 }, 'status', '--domain', $domain, '--json');
my $json = &vgo_json_from_output($outj);
if ($json) {
    my $state = $json->{'state'} || 'unknown';
    print "<p>State: ".&vgo_badge($state, $state)."</p>\n";
}

print "<p><a href='validate.cgi?domain=".&vgo_url($domain)."'>Validate</a> | ".
      "<a href='configure.cgi?domain=".&vgo_url($domain)."'>Configure</a> | ".
      "<a href='releases.cgi?domain=".&vgo_url($domain)."'>Releases</a> | ".
      "<a href='apache_config.cgi?domain=".&vgo_url($domain)."'>Apache</a> | ".
      "<a href='logs.cgi?domain=".&vgo_url($domain)."'>Logs</a> | ".
      "<a href='deploy.cgi?domain=".&vgo_url($domain)."'>Deploy</a> | ".
      "<a href='open.cgi?domain=".&vgo_url($domain)."' target='_blank'>Open site</a> | ".
      "<a href='index.cgi'>All instances</a></p>\n";

&ui_print_footer('index.cgi', 'Go Applications');
