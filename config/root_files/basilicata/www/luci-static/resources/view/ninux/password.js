'use strict';
'require view';
'require dom';
'require ui';
'require form';
'require rpc';

// Cambio password per root e admin (entrambi con UID 0). La pagina standard
// "Password del router" passa sempre 'root' al backend: chi entra come admin
// cambierebbe la password di root e non la propria. luci.setPassword accetta
// qualsiasi utente, con gli stessi permessi (luci-mod-system-config).

var formData = {
	password: {
		user: 'admin',
		pw1: null,
		pw2: null
	}
};

var callSetPassword = rpc.declare({
	object: 'luci',
	method: 'setPassword',
	params: [ 'username', 'password' ],
	expect: { result: false }
});

return view.extend({
	render: function() {
		var m, s, o;

		m = new form.JSONMap(formData, _('Password utenti'),
			_('Cambia la password di root o di admin: sono due utenti amministratori distinti, ciascuno con la sua password.'));
		s = m.section(form.NamedSection, 'password', 'password');

		o = s.option(form.ListValue, 'user', _('Utente'));
		o.value('admin', 'admin');
		o.value('root', 'root');

		o = s.option(form.Value, 'pw1', _('Nuova password'));
		o.password = true;
		o.datatype = 'minlength(6)';

		o = s.option(form.Value, 'pw2', _('Conferma la password'), ' ');
		o.password = true;
		o.renderWidget = function(/* ... */) {
			var node = form.Value.prototype.renderWidget.apply(this, arguments);

			node.querySelector('input').addEventListener('keydown', function(ev) {
				if (ev.keyCode == 13 && !ev.currentTarget.classList.contains('cbi-input-invalid'))
					document.querySelector('.cbi-button-save').click();
			});

			return node;
		};
		o.validate = function(section_id, value) {
			var pw1 = this.section.children[1].formvalue(section_id);

			return (pw1 == value) ? true : _('Le due password non coincidono');
		};

		return m.render();
	},

	handleSave: function() {
		var map = document.querySelector('.cbi-map');

		return dom.callClassMethod(map, 'save').then(function() {
			var user = formData.password.user,
			    pw1 = formData.password.pw1;

			if (pw1 == null || pw1.length == 0)
				return;

			if (pw1 != formData.password.pw2) {
				ui.addNotification(null, E('p', _('Le due password non coincidono: password non cambiata.')), 'danger');
				return;
			}

			return callSetPassword(user, pw1).then(function(success) {
				if (success)
					ui.addNotification(null, E('p', _('Password di %s cambiata.').format(user)), 'info');
				else
					ui.addNotification(null, E('p', _('Cambio della password di %s non riuscito.').format(user)), 'danger');

				formData.password.pw1 = null;
				formData.password.pw2 = null;

				dom.callClassMethod(map, 'render');
			});
		});
	},

	handleSaveApply: null,
	handleReset: null
});
