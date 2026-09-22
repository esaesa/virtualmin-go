#!/usr/bin/perl
# virtualmin-go validate.cgi — PASS/WARN/FAIL validation for one domain
use strict;
use warnings;
our (%in, %text);
do 'virtualmin-go-lib.pl';
&ReadParse();

my $domain = &vgo_request_domain();
&error('No valid domain was specified.') if !$domain;
my $inst = &vgo_assert_visible($domain);

&ui_print_header(undef, "Go Validate: $domain", '', 'go');

my ($rc, $out) = &vgo_run('validate', '--domain', $domain);
print "<pre>".&html_escape($out)."</pre>\n";
if ($rc == 0) {
    print "<p>Result: ".&vgo_badge('PASS', 'ok')."</p>\n";
}
else {
    print "<p>Result: ".&vgo_badge('FAIL', 'fail')."</p>\n";
}
print "<p><a href='status.cgi?domain=".&vgo_url($domain)."'>Status</a> | ".
      "<a href='index.cgi'>All instances</a></p>\n";

&ui_print_footer('index.cgi', 'Go Applications');
