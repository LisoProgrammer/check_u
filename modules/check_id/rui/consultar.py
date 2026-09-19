import requests

url = "https://ventanillasocial.dnp.gov.co/Home/ObtenerDatosRUI"
pre_data = {
    "id": "1043645839"
}

def consultar(pre_data):
    response = requests.post(
        url,
        data={
            "pNumDoc": pre_data["id"],
            "pTipDoc": "3"
        },
        timeout=10
    )

    #print(response.status_code)
    #print(response.headers)
    data = response.json()
    #print(response.text)
    response_format = {
        "message": "",
        "success": "",
        "data": {
            "id": "",
            "nombre_completo": ""
        }
    }
    if data["ok"] is True:
        response_format["message"] = "Se encontró información relacionada al documento suministrado"
        response_format["success"] = True
        response_format["data"]["id"] = pre_data["id"]
        response_format["data"]["nombre_completo"] = data["nombre"]
    else:
        response_format["message"] = "NO se encontró información relacionada al documento suministrado"
        response_format["success"] = False
        response_format["data"]["id"] = pre_data["id"]
    return response_format


if __name__ == "__main__":
    print(consultar(pre_data))