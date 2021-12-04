import requests

url = input("DNS do LoadBalancer:")

request_input = input("Request (get/post)")

if request_input == "get":
    response = requests.get(url)
    print(response.json())

elif request_input == "post":

    # Header
    print("Parametros do Header:")
    title = input("Title:")
    ano = input("Ano:")
    mes = input("Mes:")
    dia = input("Dia:")
    hora = input("Hora:")
    minuto = input("Minuto:")
    segundo = input("Segundo:")
    description = input("Descricao:")
    response = requests.post(url, data={
                                            "tittle": title,
                                            "pub_date": f"{ano}-{mes}-{dia}T{hora}:{minuto}",
                                            "description": description
                                        })

    print(response.json())
    