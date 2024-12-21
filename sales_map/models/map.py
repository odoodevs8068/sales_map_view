from datetime import datetime
import logging
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
from folium.plugins import MarkerCluster
import folium

_logger = logging.getLogger(__name__)


def to_friendly_date(dt):
    return dt.strftime("%B %d, %Y, %I:%M %p")

def time_ago(dt):
    now = datetime.now()
    difference = now - dt

    seconds_in_day = 86400

    days = difference.days
    hours = difference.seconds // 3600
    minutes = (difference.seconds // 60) % 60
    seconds = difference.seconds % 60

    if days > 0:
        return f"{days} days ago"
    elif hours > 0:
        return f"{hours} hours ago"
    elif minutes > 0:
        return f"{minutes} minutes ago"
    else:
        return f"{seconds} seconds ago"


class Foliummap():

    def create_folium_map(self, odoo_instance, sale_records:list=False, location:list=False, zoom=False, skip_location=False):
        map = folium.Map(location=location, zoom_start=5)
        sale_records = self.process_sale_orders(self, odoo_instance, sale_records)
        map = self.add_markers(self, sale_records, map, skip_location=skip_location, odoo_instance=odoo_instance)
        if not map: return "<p>Customer address not found! Please update the address and reload.</p>"
        folium.LayerControl().add_to(map)
        return map._repr_html_()

    def process_sale_orders(self, odoo_instance, sale_records):
        sale_record_lod = []
        base_url = odoo_instance.env['ir.config_parameter'].sudo().get_param('web.base.url')
        total_sale_records = len(sale_records)
        for count, order in enumerate(sale_records, start=1):
            _logger.info(f"{count} of {total_sale_records}")
            street = order.partner_id.street or ""
            city = order.partner_id.city or ""
            state = order.partner_id.state_id.name if order.partner_id.state_id else ""
            address = f"{street}, {city}, {state} {order.partner_id.country_id.name}".strip(", ")
            if not order.partner_id.latitude:
                gps_data = self.get_coordinates(self, address)
                if not gps_data:
                    _logger.warning(f"no gps_data! ... moving to next order...")
                    continue
                order.partner_id.write({'latitude': gps_data[0], 'longitude': gps_data[1]})
            else:
                _logger.info(f"partner already has GPS coords {(order.partner_id.latitude,order.partner_id.longitude)}")
                gps_data = (order.partner_id.latitude,order.partner_id.longitude)
            sale_order_lines = ""
            for order_line in order.order_line:
                sale_order_lines += f"<b>{order_line.product_uom_qty}</b> - {order_line.name}<br/>"
            record = {
                        'customer name': order.partner_id.name,
                        'customer id': order.partner_id.id,
                        'name': order.name,
                        'customer address': address,
                        'sale amount': int(order.amount_total),
                        'sale date': order.date_order,
                        'sale id':order.id,
                        'sale lines':sale_order_lines,
                        'gps_coordinates':gps_data,
                        'base_url':base_url,
                        }
            sale_record_lod.append(record)
        return sale_record_lod



    def add_markers(self, sale_list, map, skip_location=False, odoo_instance=False):
        gps_coords_list = []
        marker_count = 0
        marker_cluster = MarkerCluster().add_to(map)
        for sale in sale_list:
            gps_data = sale['gps_coordinates']
            if not gps_data:
                continue
            gps_coords_list.append(gps_data)
            if sale['sale date'] is not None:
                sale_date = sale['sale date']
                friendly_sale_date_str = f"{to_friendly_date(sale_date)} ({time_ago(sale_date)})"
            else:
                friendly_sale_date_str = 'No sale date info'

            action = odoo_instance.env['ir.actions.act_window'].search([('res_model', '=', 'sale.order')], limit=1)
            action_id = action.id if action else None
            menu = odoo_instance.env['ir.ui.menu'].search([('name', '=', 'Sales')], limit=1)
            menu_id = menu.id if menu else '179'

            sale_url = f"{sale['base_url']}/web#id={sale['sale id']}&menu_id={menu_id}&action={action_id}&active_id={sale['sale id']}&model=sale.order&view_type=form"

            detailed_info = f"""
            <div style="
                min-width: 350px;
                padding: 15px;
                border: 1px solid #ddd;
                border-radius: 8px;
                background-color: #f9f9f9;
                font-family: Arial, sans-serif;
                color: #333;">

                <div style="margin-bottom: 10px; font-size: 16px; font-weight: bold;">
                    <a href="{sale['base_url']}/web#id={sale['customer id']}&view_type=form&model=res.partner"
                       target="_blank"
                       style="text-decoration: none; color: #007bff;">
                        {sale['customer name']}
                    </a> - <a href="{sale_url}" target="_blank" style="text-decoration: none; color: black;">{sale['name']} </a>
                </div>

                <div style="margin-bottom: 10px; font-size: 14px; color: #555;">
                    <span>{friendly_sale_date_str}</span>
                </div>

                <div style="margin-bottom: 10px; font-size: 16px; font-weight: bold; color: #28a745;">
                    ${sale['sale amount']}
                </div>

                <div style="margin-bottom: 15px; font-size: 14px; color: #666;">
                    {sale['sale lines']}
                </div>

                <div style="margin-bottom: 15px; font-size: 14px; color: #555;">
                    <i>{sale['customer address']}</i>
                </div>


            </div>
            """
            sale_type = {'icon_color': 'green'}
            marker = folium.Marker(
                location=gps_data,
                icon=folium.Icon(color=sale_type['icon_color']),
                popup=detailed_info,
            )
            marker.add_to(marker_cluster)
            marker_count += 1
        if not skip_location:
            print("Setting map location to centroid")
            map.location = self.find_centroid(self, gps_coords_list)
        return map

    def get_coordinates(self, address):
        geolocator = Nominatim(user_agent="myGeocodeApp_v1")
        try:
            location = geolocator.geocode(address, timeout=10)
            if location:
                _logger.info(f"location found for {address}! - {location.latitude, location.longitude}")
                return (location.latitude, location.longitude)
            else:
                _logger.warning(f"location not found for address {address} ")
                return []
        except GeocoderTimedOut:
            return []
        except GeocoderUnavailable as e:
            return []
        except Exception as e:
            return []

    def find_centroid(self, coords):
        if not coords:
            return None

        sum_lat = 0
        sum_lon = 0
        for lat, lon in coords:
            sum_lat += lat
            sum_lon += lon

        count = len(coords)
        return sum_lat / count, sum_lon / count

