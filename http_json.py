import requests

def http_method(method : str, base_url : str, sub_url : str, data={}, token="", init=False):
    assert method in ["GET", "POST", "PUT"]
    headers = {}
    headers['Accept'] = "application/json"
    headers['Content-Type'] = "application/json"
    if init is True:
        headers['X-Auth-Token'] = token
    else:
        headers['Authorization'] = token

    if method == "GET":
        response = requests.get(base_url+sub_url, headers=headers)
    elif method == "POST":
        response = requests.post(base_url+sub_url, headers=headers, json=data)
    elif method == "PUT":
        response = requests.put(base_url+sub_url, headers=headers, json=data)
    else:
        return {}
    status_code = response.status_code
    res = {}
    if status_code == 200:
        res = response.json()
    # print(status_code, res)
    return res
