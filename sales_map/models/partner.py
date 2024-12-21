from odoo import api, fields, models, tools, _

from .map import Foliummap
from geopy.geocoders import Nominatim
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)

class ResPartner(models.Model):
    _inherit = 'res.partner'

    gps_coordinates = fields.Char(string='GPS Coordinates', compute="_compute_gps_coordinates")
    latitude = fields.Float(string='Latitude')
    longitude = fields.Float(string='Longitude')

    @api.onchange('street','city','state_id', 'country_id', 'zip')
    def _onchange_street_get_coordinates(self):
        if self.street or (self.city and self.state_id):
            street = self.street or ""
            city = self.city or ""
            state = self.state_id.name if self.state_id else ""
            address = f"{street} {city} {state} {self.country_id.name}"
            geolocator = Nominatim(user_agent="myGeocodeApp_v1")
            try:
                location = geolocator.geocode(address, timeout=10)
                if location:
                    _logger.info(f"location found for {address}! - {location.latitude, location.longitude}")
                    self.latitude = location.latitude
                    self.longitude = location.longitude
                    self.write({
                        'latitude': location.latitude,
                        'longitude': location.longitude
                    })
                else:
                    _logger.warning(f"location not found for address {address} ")
            except Exception as e:
                _logger.warning(f"error at {e}")

    @api.onchange('street','city','state_id', 'country_id', 'zip')
    def _compute_gps_coordinates(self):
        if self.latitude and self.longitude:
            self.gps_coordinates = f"{self.latitude}, {self.longitude}"
        else: self.gps_coordinates = "GPS Not Available"

class Saleorder(models.Model):
    _inherit = 'sale.order'

    def get_sales(self):
        query = """
            SELECT 
                so.name AS name,
                so.id AS id,
                SUM(so.amount_total) AS total_amt
            FROM 
                sale_order so
            WHERE 
                so.state != 'cancel'
            GROUP BY 
                so.name, so.id
            ORDER BY 
                total_amt DESC;
            """
        return query

    def get_sales_of_map(self, sale_orders, customers):
        for customer in customers['records']:
            partner = self.env['res.partner'].search([('name', '=', customer['name'])], limit=1)
            customer_orders = self.env['sale.order'].search([('partner_id', '=', partner.id)],
                                                            order='amount_total desc', limit=5)
            sale_orders.extend(customer_orders)
        return sale_orders

    @api.model
    def update_map_html(self, location:list=[39.8283, -98.5795], zoom=5, skip_location=False, limit_records:int=False, customer=False,  mapFilter=False):
        sale_orders = []
        if not customer:
            customers = self.get_records()
            sale_orders = self.get_sales_of_map(sale_orders, customers)
        else:
            sale_orders = self.env['sale.order'].search([('partner_id', '=', customer) if mapFilter == 'Customer' else ('id', '=', customer)], order='amount_total desc')
        folium_instance = Foliummap
        map_html = folium_instance.create_folium_map(folium_instance, self, sale_records=sale_orders, location=location, zoom=zoom, skip_location=skip_location)
        return {'map_html': map_html}

    @api.model
    def get_records(self, filt=None):
        query = self.get_customer_query()  if filt in (None, 'Customer') else self.get_sales()
        self.env.cr.execute(query)
        customers_by_sales = self.env.cr.dictfetchall()
        customers = {
            'records': customers_by_sales,
        }
        return customers

    def get_customer_query(self):
        query = """
            SELECT 
                partner.name AS name,
                partner.id AS id,
                SUM(so.amount_total) AS total_amt
            FROM 
                sale_order so
            JOIN 
                res_partner partner ON so.partner_id = partner.id
            WHERE 
                so.state != 'cancel'
            GROUP BY 
                partner.name, partner.id
            ORDER BY 
                total_amt DESC;
            """
        return query
