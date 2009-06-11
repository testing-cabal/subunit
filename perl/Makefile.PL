use ExtUtils::MakeMaker;
WriteMakefile(
    'NAME'	=> 'Subunit',
    'VERSION_FROM' => 'lib/Subunit.pm',
	'test' => { 'TESTS' => 'tests/*.pl' }
);
