import os
from random import randint
import requests
from dotenv import load_dotenv


class VkResponseException(BaseException):
    pass


def raise_for_error(response):
    response.raise_for_status()
    try:
        raise VkResponseException(response.json()['error']['error_code'], response.json()['error']['error_msg'])
    except KeyError:
        pass


def vk_request(http_method, vk_method, **kwargs):
    api_url = f'https://api.vk.com/method/{vk_method}'
    response = getattr(requests, http_method)(api_url, **kwargs)
    raise_for_error(response)

    return response.json()


def download_image(url):
    image_filename = url.split('/')[-1]

    response = requests.get(url=url)
    response.raise_for_status()

    with open(image_filename, 'wb') as image_file:
        image_file.write(response.content)

    return image_filename


def download_random_xkcd_comics():
    xkcb_url = 'https://xkcd.com/info.0.json'
    response = requests.get(url=xkcb_url)
    response.raise_for_status()
    last_comics_number = response.json()['num']
    rnd_page = randint(1, last_comics_number)

    xkcb_url = f'https://xkcd.com/{rnd_page}/info.0.json'
    response = requests.get(url=xkcb_url)
    response.raise_for_status()

    image_url = response.json()['img']
    comment = response.json()['alt']

    return download_image(url=image_url), comment


def get_vk_groups(access_token):
    params = {'access_token': access_token,
              'v': '5.95'}
    return vk_request('get', 'groups.get', params=params)


def get_vk_walluploadserver(token, group_id):
    params = {
        'access_token': token,
        'v': 5.103,
        'group_id': group_id,
    }

    return vk_request('get', 'photos.getWallUploadServer', params=params)['response']['upload_url']


def upload_photo_to_vk_server(token, group_id, path_to_photo, caption):
    upload_server = get_vk_walluploadserver(token=token, group_id=group_id)

    with open(path_to_photo, 'rb') as image_file:
        files = {'photo': image_file}
        response = requests.post(url=upload_server, files=files)

    raise_for_error(response)
    response_data = response.json()

    if not response_data['photo']:
        raise VkResponseException(0, 'Image upload error')

    params = {
        'access_token': token,
        'v': 5.103,
        'photo': response_data['photo'],
        'server': response_data['server'],
        'hash': response_data['hash'],
        'group_id': group_id,
        'caption': caption
    }

    return vk_request('post', 'photos.saveWallPhoto', params=params)


def publish_photo_to_wall(token, owner_id, attachments, message):
    params = {
        'access_token': token,
        'v': 5.103,
        'from_group': 1,
        'message': message,
        'attachments': attachments,
        'owner_id': owner_id,
    }

    return vk_request('post', 'wall.post', params=params)


def main():
    load_dotenv()
    api_token = os.getenv('VK_ACCESS_TOKEN')
    vk_group_id = int(os.getenv('VK_GROUP_NAME'))

    path_to_comics_file, xkcd_comics_comment = download_random_xkcd_comics()

    response = upload_photo_to_vk_server(token=api_token, group_id=vk_group_id,
                                         path_to_photo=path_to_comics_file, caption=xkcd_comics_comment)['response'][0]
    owner_id = response['owner_id']
    media_id = response['id']

    publish_photo_to_wall(token=api_token, owner_id=f'-{vk_group_id}',
                          attachments=f'photo{owner_id}_{media_id}', message=xkcd_comics_comment)

    os.unlink(path_to_comics_file)
    exit(0)


if __name__ == "__main__":
    main()
