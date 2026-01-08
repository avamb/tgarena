<?php /**          _     _            _           ____
 *       __      _(_) __| | __ _  ___| |_  __   _|___ \
 *       \ \ /\ / / |/ _` |/ _` |/ _ \ __| \ \ / / __) |
 *        \ V  V /| | (_| | (_| |  __/ |_   \ V / / __/ 
 *         \_/\_/ |_|\__,_|\__, |\___|\__|___\_/ |_____|
 *                         |___/                        © consta.prokhorov 2023 */ ?>

<link rel="stylesheet" href="<?php print $basename; ?>lib/cdn/jquery.fancybox-3.5.7.min.css" />

<?php
$core_styles = _css($basename, 'styles/core.css');
if ($core_styles == $basename.'styles/core.css') $core_styles = $basename.'styles/core.css';
?>
<link rel="stylesheet" href="<?php print $core_styles; ?>?q=v<?php print $version; ?>" />

<link rel="stylesheet" href="<?php print $basename; ?>custom/style.css?q=v<?php print time(); ?>" />