/** @odoo-module **/

import { Component, onMounted, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import rpc from "web.rpc";

function _defaultOptions() {
    return {
        type: 'fixed',
        size: 'medium',
        container: null,
        position: {
            top: 'auto',
            bottom: '0px',
            left: 'auto',
            right: '0px',
        },
        animation: false,
        trayicon: false
    };
};

function _getSettings() {
    var options = _defaultOptions();
    return rpc.query({
        model: 'res.config.settings',
        method: 'get_dialer_settings',
        args: ['hello'],
    }, {
        shadow: true,
        silent: true,
    }).then(function (data) {
        if (data.size !== undefined) {
            options.size = data.size;
        }
        if (data.trayicon !== undefined) {
            options.trayicon = data.trayicon;
        }
        if (data.position !== undefined) {
            options.position = {
                top: 'auto',
                bottom: 'auto',
                left: 'auto',
                right: 'auto',
            };
            switch (data.position) {
                case 'tr':
                    options.position.top = '40px';
                    options.position.right = '0px';
                    break;
                case 'br':
                    options.position.bottom = '0px';
                    options.position.right = '0px';
                    break;
                case 'bl':
                    options.position.bottom = '0px';
                    options.position.left = '0px';
                    break;
                case 'tl':
                    options.position.top = '40px';
                    options.position.left = '0px';
                    break;
                default:
                    options.position.bottom = '0px';
                    options.position.right = '0px';
            }
        }
        return options;
    })
        .catch(() => { return options; });
}

// Listener callback on number link, return phone number string
function clickOnNbrCallback(e) {
    e = window.e || e;
    var result = null;

    if (
        e.target.tagName !== undefined
        && e.target.tagName === 'A'
        && e.target.outerHTML.includes('href="tel:')
    ) {
        result = e.target.pathname;
    } else if (
        e.target.parentElement !== undefined
        && e.target.parentElement.tagName !== undefined
        && e.target.parentElement.tagName === 'A'
        && e.target.parentElement.outerHTML.includes('href="tel:')
    ) {
        result = e.target.parentElement.pathname;
    } else {
        // No number found in link
        return null;
    }

    // Prevent default action: select application
    if (result !== null) {
        e.preventDefault(); e.stopImmediatePropagation(); e.stopPropagation();
    }

    return result;
}

export class DialerBtn extends Component {
    showNotification(notifName) {
        var text = 'Dialer ready';
        var type = 'success';

        if (notifName !== 'ready') {
            text = 'Dialer not ready';
            type = 'info';
        }

        setTimeout(() => {
            this.notification.add(text, { type })
        }, 1000);
    }

    /* Popup the dialer when click on a phone number */
    popupDialerOnClick(num) {
        // SDK lib not fully loaded
        if (typeof RingoverSDK === 'undefined') {
            this.showNotification('notReady');

            return;
        }

        this.dialerSdk.dial(num);
        if (!this.dialerSdk.isDisplay()) {
            this.dialerSdk.show();
        }
    }

    /* Toggle the dialer when click on systray icon */
    toggleDialer() {

        // SDK lib not fully loaded
        if (typeof RingoverSDK === 'undefined') {
            this.showNotification('notReady');

            return;
        }

        this.dialerSdk.on('dialerReady', (e) => { /* dialer ready */ });
        this.dialerSdk.toggle();
    }

    setup() {
        // Initiate dialer SDK to null
        this.dialerSdk = null;
        this.notification = useService("notification");
        this.state = useState({ dialer_options: _defaultOptions(), dialer_status: 'logged_out', dialer_displayed: false });

        onWillStart(async () => {
            _getSettings()
                .then((options) => {
                    if (typeof RingoverSDK !== 'undefined') {
                        // Create instance
                        this.dialerSdk = new RingoverSDK(options);
                        this.dialerSdk.generate();
                        this.state.dialer_status = 'generated';
                        this.dialerSdk.hide();
                        this.dialerSdk.on('dialerReady', (e) => { this.state.dialer_status = 'logged_in'; });
                        this.dialerSdk.on('changePage', (e) => { if (e.data.page && e.data.page === 'login') { this.state.dialer_status = 'generated'; } });
                        this.dialerSdk.on('ringingCall', (e) => { if (!this.dialerSdk.isDisplay()) { this.dialerSdk.show(); } });
                    }
                })
                .catch(() => { this.showNotification('notReady'); });
        });

        onMounted(() => {
            if (document.addEventListener) {
                document.addEventListener(
                    'click',
                    (e) => {
                        const numInLink = clickOnNbrCallback(e);
                        if (numInLink !== null) {
                            this.popupDialerOnClick(numInLink);
                        }
                    },
                    false
                );
            } else {
                document.attachEvent(
                    'onclick',
                    (e) => {
                        const numInLink = clickOnNbrCallback(e);
                        if (numInLink !== null) {
                            this.popupDialerOnClick(numInLink);
                        }
                    }
                );
            }
        });
    }
}
DialerBtn.template = "ringover.dialer.systray";
DialerBtn.components = {};

export const systrayItem = {
    Component: DialerBtn,
};
registry.category("systray").add("ringover.dialer.systray", systrayItem, { sequence: 100 });