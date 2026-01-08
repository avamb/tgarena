'use strict';

var region;
(() => {
	let l = window.navigator ? (window.navigator.language || window.navigator.systemLanguage || window.navigator.userLanguage) : ('en');
	['-', '_'].forEach(symbol => {
		l = (l.search(symbol) > 0) ? l.substring(0, l.search(symbol)).toLowerCase() : l.toLowerCase();
	});
	
	switch (l) {
		case 'ru':// russian
			region = {
				lng:        'ru',
				local:      'ru_RU',
				localJSON:  'ru_RU.json',
				success:    'https://bilw.ru/pay_s.html',
				fail:       'https://bilw.ru/pay_f.html',
				agr:        'https://bilw.ru/agreement.html',
				requestURL: 'https://api.bil24.pro',
				version:    'ru',
			};
			break;
			
		case 'hy':// hayeren
			region = {
				lng:        'am',
				local:      'am_AM',
				localJSON:  'am_AM.json',
				success:    'https://tixgear.com/pay_s.html',
				fail:       'https://tixgear.com/pay_f.html',
				agr:        'https://tixgear.com/agreement.html',
				requestURL: 'https://api.tixgear.com',
				version:    'am',
			};
		break;
		
		/*case 'tt':// tatar
			region = {
				lng:        'tt',
				local:      'tt_RU',
				localJSON:  'tt_RU.json',
				success:    'https://bilw.ru/pay_s.html',
				fail:       'https://bilw.ru/pay_f.html',
				agr:        'https://bilw.ru/agreement.html',
				requestURL: 'https://api.bil24.pro',
				version:    'tt',
			};
		break;*/
			
		default:// en // english
			region = {
				lng:        'en',
				local:      'en_EN',
				local_json: 'en_EN.json',
				success:    'https://tixgear.com/pay_s.html',
				fail:       'https://tixgear.com/pay_f.html',
				agr:        'https://tixgear.com/agreement.html',
				requestURL: 'https://api.tixgear.com',
				version:    'en',
			};
	}
})();