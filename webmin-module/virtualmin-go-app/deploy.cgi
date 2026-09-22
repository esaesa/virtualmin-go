#!/usr/bin/perl
# virtualmin-go-app deploy.cgi — deploy a release (upload tarball / git source)
# Domain owners may deploy only their own instances; see vgo_assert_visible.
use strict;
use warnings;
our (%in, %text, %config);
do 'virtualmin-go-app-lib.pl';
&ReadParse();

my @instances = &vgo_visible_instances();
&error('No Go instances are visible to your login.') if !@instances;

my ($message, $type, $details) = ('', 'info', '');
my $method = uc($ENV{'REQUEST_METHOD'} || 'GET');

if ($method eq 'POST' && $in{'deploy'}) {
    &vgo_require_write('application deploy');
    my $domain = lc($in{'domain'} || '');
    my $inst = &vgo_assert_visible($domain);
    my $kind = $in{'kind'} || 'artifact';
    my $go_mode = ($in{'go_mode'} || 'prod') eq 'dev' ? 'dev' : 'prod';
    my $version = $in{'version'} || '';
    &error('Invalid version string.') if $version ne '' && $version !~ /^[A-Za-z0-9_.+~-]{1,64}$/;
    my $health = $in{'health_path'} || '/health';
    &error('Health path must start with /.') if $health !~ m{^/};
    my @args = ('deploy', '--domain', $domain, '--mode', $go_mode, '--health-path', $health);
    push(@args, '--version', $version) if $version ne '';
    my $cleanup;
    if ($kind eq 'artifact') {
        my $tmp = $in{'artifact'} || '';
        my $orig = $in{'artifact_filename'} || 'upload.tar.gz';
        &error('No artifact file was uploaded.') if !$tmp || !-f $tmp;
        &error('Artifact must be a .tar.gz file.') if $orig !~ /\.t(?:ar\.)?gz$/i;
        my $size = -s $tmp || 0;
        my $cap = 512 * 1024 * 1024;
        &error('Artifact exceeds the 512 MiB upload cap.') if $size > $cap;
        push(@args, '--artifact', $tmp);
        $cleanup = $tmp;
    }
    elsif ($kind eq 'source') {
        my $url = $in{'source_url'} || '';
        &error('Source URL must be https:// or git@ (no file://).')
            if $url !~ m{^https://[A-Za-z0-9._~:/?#@!$&()*+,;=%-]+$} && $url !~ m{^git@[A-Za-z0-9._-]+:[A-Za-z0-9._/-]+$};
        my $branch = $in{'branch'} || '';
        my $commit = $in{'commit'} || '';
        my $package = $in{'package'} || './...';
        my $app = $in{'app_name'} || '';
        &error('Invalid branch.') if $branch ne '' && $branch !~ /^[A-Za-z0-9_.\/-]{1,128}$/;
        &error('Invalid commit (want hex sha).') if $commit ne '' && $commit !~ /^[0-9a-f]{7,40}$/;
        &error('Invalid package path.') if $package !~ m{^[A-Za-z0-9_./-]{1,128}$} || $package =~ /\.\./;
        &error('Invalid app name.') if $app ne '' && $app !~ /^[A-Za-z0-9_.-]{1,64}$/;
        push(@args, '--source', $url);
        push(@args, '--branch', $branch) if $branch ne '';
        push(@args, '--commit', $commit) if $commit ne '';
        push(@args, '--package', $package, '--app-name', $app) if $app ne '';
        push(@args, '--package', $package) if $app eq '';
    }
    else {
        &error('Unknown deploy kind.');
    }
    my ($rc, $out) = vgo_run_opts({ timeout => 900 }, @args);
    unlink($cleanup) if $cleanup && -f $cleanup;
    $message = $rc == 0 ? 'Deploy completed — release is live.' : 'Deploy failed; previous release (if any) was restored.';
    $type = $rc == 0 ? 'good' : 'bad';
    $details = $out;
}

&ui_print_header(undef, 'Go Deploy', '', 'go');
if ($message) {
    print "<p><b>".vgo_html($message)."</b></p>\n";
    print "<pre>".vgo_html($details || '')."</pre>\n" if $details;
}
print "<p>Deploy a release to one of your instances. Prebuilt <tt>.tar.gz</tt> artifacts (manifest + <tt>bin/</tt>) go live through the atomic flow; git sources are compiled on the VPS with the instance toolchain. Failed deploys restore the previous release automatically.</p>\n";
print &ui_form_start('deploy.cgi', 'form-data');
print &ui_table_start('Deploy a release', 'width=100%', 2);
my $first = $instances[0]->{'DOMAIN'};
my $opts = join('', map {
    my $d = $_->{'DOMAIN'};
    "<option value='".vgo_html($d)."'".($d eq ($in{'domain'} || $first) ? ' selected' : '').">".vgo_html($d)."</option>";
} @instances);
print &ui_table_row('Domain', "<select name='domain'>$opts</select>");
print &ui_table_row('Kind',
    "<select name='kind'><option value='artifact'>Prebuilt .tar.gz upload</option><option value='source'>Git source (build on VPS)</option></select>");
print &ui_table_row('Artifact file', "<input type='file' name='artifact' accept='.tar.gz,.tgz'>");
print &ui_table_row('Source URL', &ui_textbox('source_url', '', 50));
print &ui_table_row('Branch', &ui_textbox('branch', '', 20));
print &ui_table_row('Commit (sha)', &ui_textbox('commit', '', 45));
print &ui_table_row('Go package', &ui_textbox('package', './...', 30));
print &ui_table_row('App name', &ui_textbox('app_name', '', 30));
print &ui_table_row('Version (optional)', &ui_textbox('version', '', 20));
print &ui_table_row('Health path', &ui_textbox('health_path', '/health', 20));
print &ui_table_row('Mode',
    "<select name='go_mode'><option value='prod'>prod (compiled binary)</option><option value='dev'>dev (go run)</option></select>");
print &ui_table_end();
print &ui_form_end([['deploy', 'Deploy now']]);
print "<p><a href='index.cgi'>All instances</a></p>\n";
&ui_print_footer('index.cgi', 'Go Applications');
