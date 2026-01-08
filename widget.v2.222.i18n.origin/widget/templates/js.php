<?php /**          _     _            _           ____
 *       __      _(_) __| | __ _  ___| |_  __   _|___ \
 *       \ \ /\ / / |/ _` |/ _` |/ _ \ __| \ \ / / __) |
 *        \ V  V /| | (_| | (_| |  __/ |_   \ V / / __/ 
 *         \_/\_/ |_|\__,_|\__, |\___|\__|___\_/ |_____|
 *                         |___/                        © consta.prokhorov 2023 */ ?>

<?php foreach ([
	'lib/cdn/jquery-1.11.3.min',
	'lib/ui/jquery-ui.min',
	'lib/cdn/jquery.fancybox-3.5.7.min',
	'lib/cdn/angular-1.5.8.min',
	'lib/cdn/angular-animate-1.5.8.min',
	'lib/cdn/angular-resource-1.5.8',
	'lib/cdn/angular-sanitize-1.5.8.min',
	'lib/cdn/ngStorage-0.3.6.min',
	'lib/angular-growl/angular-growl.min',
	'lib/panzoom.min',
	'lib/jquery.maskedinput.min',
	'lib/modernizr-custom',
	'lib/hammer.min',
	'lib/moment.min',
	'lib/jquery.svg-seat-plan',
	'custom/config/reg',
	'scripts/core',
	'scripts/'.$scriptname,
	'scripts/header',
	'scripts/basket',
] as $script): ?>
	<script src="<?php print $basename; ?><?php print $script; ?>.js?q=v<?php print $version; ?>"></script>
<?php endforeach; ?>

<?php include_once($basename.'custom/include.php'); ?>
<script src="<?php print $basename; ?>custom/script.js?q=v<?php print time(); ?>"></script>