#!/usr/bin/perl
# virtualmin-go open.cgi — bounce to the public site (mirrors PB open.cgi).
use strict;
use warnings;
our (%in, %text);
do 'virtualmin-go-lib.pl';
&ReadParse();

my $domain = &vgo_request_domain();
&error('No valid domain was specified.') if !$domain;
my $inst = &vgo_assert_visible($domain);
&redirect("https://$domain/");
