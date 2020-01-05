import requests
import os


def check_response(response, description):

    response.raise_for_status()
    json_response = response.json()
    if 'errors' in json_response:
    #https://docs.moltin.com/api/basics/errors
        raise requests.exceptions.HTTPError('%s, %S'%(description, json_response['errors']))
    return json_response


def fetch_bearer_token():

    client_id = os.environ.get['MOLTIN_CLIENT_ID']
    data = {
      'client_id': client_id,
      'grant_type': 'implicit'
    }
    response = requests.post('https://api.moltin.com/oauth/access_token', data=data)
    checked_response = check_response(response, 'Failed to fetch Bearer Token')
    token = checked_response['access_token']
    return token


def fetch_products():

    token = fetch_bearer_token()
    headers = {'Authorization': 'Bearer %s'%(token)}

    url='https://api.moltin.com/v2/products/'
    response = requests.get(url, headers=headers)
    checked_response = check_response(response, 'Failed to fetch products')
    products = checked_response['data']
    name_and_id_pairs = []
    for product in products:
        product_name = product['name']
        product_id = product['id']
        name_and_id = (product_name, product_id)
        name_and_id_pairs.append(name_and_id)
    return name_and_id_pairs


def fetch_product_data(prod_id):

    token = fetch_bearer_token()
    headers = {'Authorization': 'Bearer %s'%(token)}

    url = 'https://api.moltin.com/v2/products/%s'%(prod_id)
    response = requests.get(url, headers=headers)
    checked_response = check_response(response, 'Failed to fetch product data')
    _data = checked_response['data']
    name = _data['name']
    price = '%s$ for 1pc'%(_data['price'][0]['amount']*0.01)
    stock = '%s pcs on stock'%(_data['meta']['stock']['level'])
    description = _data['description']
    media_id = _data['relationships']['main_image']['data']['id']
    url = 'https://api.moltin.com/v2/files/%s'%(media_id)
    response = requests.get(url, headers=headers)
    checked_response = check_response(response, 'Failed to fetch product photo')
    photo_url = checked_response['data']['link']['href']
    product_data = {
        'name': name,
        'price': price,
        'stock': stock,
        'description': description,
        'photo_url': photo_url,
    }
    return product_data


def delete_item(user_id, query):

    token = fetch_bearer_token()
    headers = {'Authorization': 'Bearer %s'%(token)}

    prod_id = query.data[6:]
    url = 'https://api.moltin.com/v2/carts/%s/items/%s'%(user_id, prod_id)
    response = requests.delete(url=url, headers=headers)
    check_response(response, 'Failed to delete item')


def fetch_products_in_cart(user_id):

    token = fetch_bearer_token()
    headers = {'Authorization': 'Bearer %s'%(token)}

    url = 'https://api.moltin.com/v2/carts/%s/items'%(user_id)
    response = requests.get(url=url, headers=headers)
    checked_response = check_response(response, 'Failed to fetch products in cart')
    items_in_cart = checked_response['data']
    return items_in_cart


def create_customer(name, email):

    token = fetch_bearer_token()
    headers = {
        'Authorization': 'Bearer %s'%(token),
        'Content-Type': 'application/json',
    }
    url = 'https://api.moltin.com/v2/customers'
    data = { 'data': {
           'type': 'customer',
           'name': name,
           'email': email,
           }
    }
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    json_response = response.json()
    return False if 'errors' in json_response else True


def add_to_cart(pcs, prod_id, user_id):

    token = fetch_bearer_token()
    headers = {
        'Authorization': 'Bearer %s'%(token),
        'Content-type': 'application/json; charset=utf-8',
        }

    data = {'data':
        {
            'id':prod_id,
            'type':'cart_item',
            'quantity':pcs,
        }
    }
    url = 'https://api.moltin.com/v2/carts/%s/items'%(user_id)
    response = requests.post(url=url, headers=headers, json=data)
    check_response(response, 'Failed to add to cart')
