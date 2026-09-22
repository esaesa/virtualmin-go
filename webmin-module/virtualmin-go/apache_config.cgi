#!/usr/bin/perl
# virtualmin-go apache_config.cgi — read-only view of the managed proxy
# block, coexistence markers, redirects, and configtest state.
use strict;
use warnings;
our (%in, %text);
do 'virtualmin-go-lib.pl';
&ReadParse();

my $domain = &vgo_request_domain();
&error('No valid domain was specified.') if !$domain;
my $inst = &vgo_assert_visible($domain);

&ui_print_header(undef, "Go Apache Config: $domain", '', 'go');
my $vhost = $inst->{'APACHE_VHOST_FILE'} || '(unknown)';
print "<p>Vhost file: <tt>".vgo_html($vhost)."</tt></p>\n";
my $block = '';
if ($vhost ne '(unknown)' && -f $vhost) {
    open(my $fh, '<', $vhost) || &error("Cannot read vhost: $!");
    my $inblock = 0;
    while (my $line = <$fh>) {
        $inblock = 1 if index($line, "BEGIN VIRTUALMIN-GO $domain") >= 0;
        $block .= $line if $inblock;
        if (index($line, "END VIRTUALMIN-GO $domain") >= 0) { $block .= ''; last; }
    }
    close($fh);
}
if ($block ne '') {
    print "<p>Managed Go block (module-owned):</p>\n";
    print "<pre>".vgo_html($block)."</pre>\n";
}
else {
    print "<p>No managed Go block present (expected before first deploy, or after disable).</p>\n";
}
my $pb = 'absent';
if ($vhost ne '(unknown)' && -f $vhost) {
    open(my $vf, '<', $vhost) || &error("Cannot read vhost: $!");
    local $/;
    my $all = <$vf>;
    close($vf);
    $pb = 'present (must sort before Go /)' if index($all, "BEGIN VIRTUALMIN-POCKETBASE $domain") >= 0;
}
print "<p>PocketBase <tt>/pb/</tt> block: <b>".vgo_html($pb)."</b> — never touched by this module.</p>\n";
my ($rc, $out) = vgo_run_opts({ timeout => 60 }, 'validate', '--domain', $domain);
my @checks = vgo_parse_checks($out);
my @proxy = grep { $_->{'message'} =~ /proxy|redirect|Apache|marker/i } @checks;
if (@proxy) {
    print "<table class='ui_table' width='100%'>\n";
    for my $c (@proxy) {
        print "<tr><td>".vgo_html($c->{'status'})."</td><td>".vgo_html($c->{'message'})."</td></tr>\n";
    }
    print "</table>\n";
}
print "<p>Scheme redirects are Virtualmin-owned — manage them with <tt>virtualmin list-redirects --domain $domain</tt>.</p>\n";
print "<p><a href='status.cgi?domain=".vgo_url($domain)."'>Status</a> | <a href='index.cgi'>All instances</a></p>\n";
&ui_print_footer('index.cgi', 'Go Applications');
