import requests

public_url = "https://disk.yandex.ru/d/Gfueb1nrYbtGow"
url = f"https://cloud-api.yandex.net/v1/disk/public/resources?public_key={public_url}"
response = requests.get(url)

print("Status Code:", response.status_code)
print("Response Headers:", response.headers)
print("Response Text:", response.text)
