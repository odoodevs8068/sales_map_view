odoo.define('sales_map.sales_maps_view', function (require) {
'use strict';

    var AbstractAction = require('web.AbstractAction');
    var core = require('web.core');
    var rpc = require('web.rpc');
    var web_client = require('web.web_client');
    var _t = core._t;
    var QWeb = core.qweb;
    var datepicker = require('web.datepicker');
    var time = require('web.time');
    var framework = require('web.framework');
    var self = this;

    var SaleMap = AbstractAction.extend({
        contentTemplate: 'Sales_map',
        events: {
            'input #customer-input-search': '_onCustomerSearch',
            'click .customer-row': '_onCustomerRowClick',
            'change #map_filt': 'OnchangeMapFilt'
        },

        init: function(parent, context) {
            this._super(parent, context);
        },

        willStart: function() {
            var self = this;
            return this._super().then(function() {
                console.log("Rendering dashboards...");
                var get_map_values = self._rpc({
                    model: "sale.order",
                    method: "update_map_html",
                }).then(function(res){
                    self.map_html = res['map_html'];
                });

                var get_customers = self._rpc({
                    model: "sale.order",
                    method: "get_records",
                }).then(function(res){
                    self.records = res['records'];
                });
                return $.when(get_map_values, get_customers);
            });
        },

        start: function() {
            var self = this;
            this.set("title", 'Sales Map');
            this.initializeClock();
            return this._super().then(function() {
            });
        },

        render_dashboards: function() {
            var self = this;
            self.$('.Mapview_main').append(QWeb.render("Sales_map", {widget: self}));
        },

        initializeClock: function() {
            var self = this;

            function updateClock() {
                var currentTime = new Date();
                var hours = String(currentTime.getHours()).padStart(2, '0');
                var minutes = String(currentTime.getMinutes()).padStart(2, '0');
                var seconds = String(currentTime.getSeconds()).padStart(2, '0');
                var timeString = `${hours}:${minutes}:${seconds}`;
                var day = String(currentTime.getDate()).padStart(2, '0');
                var month = String(currentTime.getMonth() + 1).padStart(2, '0');
                var year = currentTime.getFullYear();
                var dateString = `${day}/${month}/${year}`;
                var timeElement = document.getElementById('currentTime');
                var dateElement = document.getElementById('currentDate');

                if (timeElement) {
                    timeElement.textContent = timeString;
                }
                if (dateElement) {
                    dateElement.textContent = dateString;
                }
            }

            this.$el.ready(function() {
                updateClock();
                setInterval(updateClock, 1000);
            });
        },

        OnchangeMapFilt: function(ev) {
            var self = this;
            var referesh = true
            self._onCustomerRowClick(referesh);
            var mapFilter = self.$("#map_filt").val();
            self._rpc({
                    model: "sale.order",
                    method: "get_records",
                    args:[mapFilter],
            }).then(function(res){
                    self.records = res.records;
                    self.renderCustomerTable(self.records);
                });
            },

            _onCustomerSearch: function(event) {
                var self = this;
                var searchTerm = $(event.currentTarget).val().toLowerCase();
                var filteredCustomers = [];

                if (self.records && self.records.length > 0) {
                    filteredCustomers = self.records.filter(function(customer) {
                        return customer.name.toLowerCase().includes(searchTerm);
                    });
                }
                filteredCustomers.sort(function(a, b) {
                    if (a.name.toLowerCase().startsWith(searchTerm)) return -1;
                    if (b.name.toLowerCase().startsWith(searchTerm)) return 1;
                    return 0;
                });
                self.renderCustomerTable(filteredCustomers);
            },

            renderCustomerTable: function(customers) {
                var self = this;
                var $tableBody = self.$('.customers_by_sales_table tbody');
                $tableBody.empty();
                customers.forEach(function(customer) {
                    var $row = $('<tr>')
                        .addClass('customer-row')
                        .attr('data-customer-id', customer.id)
                        .append($('<td>')
                            .css('text-align', 'left')
                            .html(`<a>${customer.name}</a>`))
                        .append($('<td>').text(customer.total_amt));
                    $tableBody.append($row);
                });
                if (customers.length === 0) {
                    var $noResultsRow = $('<tr>')
                        .append($('<td>')
                            .attr('colspan', 2)
                            .css('text-align', 'center')
                            .text('No matching records found.'));
                    $tableBody.append($noResultsRow);
                }
            },

        _onCustomerRowClick: function(event, referesh) {
            var self = this;
            var mapFilter = self.$("#map_filt").val();
            if (referesh === true) {
                var args = [[39.8283, -98.5795], 5, false, false, false, mapFilter];
            } else {
                var customerId = $(event.currentTarget).data('customer-id');
                var args = [[39.8283, -98.5795], 5, false, false, customerId, mapFilter];
            }
            console.log('Customer ID:', customerId);
            self._rpc({
                    model: 'sale.order',
                    method: 'update_map_html',
                    args: args
                }).then(function (result) {
                    var $map = self.$('.map_html_container');
                    if ($map.length) {
                        $map.empty();
                        var $div = $('<div>').html(result.map_html);
                        $map.append($div);
                    } else {
                        console.error('Map container not found');
                    }
                });
        },

    });

    core.action_registry.add('sales_map.sales_maps_view', SaleMap);

    return SaleMap;
});
