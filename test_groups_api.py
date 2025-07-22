import requests
import json

# URL base da API
BASE_URL = "http://localhost:5000"

def test_groups_api():
    """Testa a API de grupos"""
    
    print("=== TESTANDO API DE GRUPOS ===\n")
    
    # Primeiro fazer login para obter token (você precisará substituir pelas credenciais corretas)
    print("1. Fazendo login...")
    login_response = requests.post(f"{BASE_URL}/login", 
                                 json={"username": "admin", "password": "admin"})
    
    if login_response.status_code == 200:
        token = login_response.json().get('access_token')
        headers = {'Authorization': f'Bearer {token}'}
        print(f"✅ Login realizado com sucesso")
    else:
        print(f"❌ Erro no login: {login_response.status_code}")
        print(f"Resposta: {login_response.text}")
        return
    
    print("\n2. Listando grupos...")
    # Listar grupos
    response = requests.get(f"{BASE_URL}/groups", headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Resposta: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    
    if response.status_code == 200:
        print("✅ Listagem de grupos funcionando")
    else:
        print("❌ Erro na listagem de grupos")
        return
        
    print("\n3. Criando novo grupo...")
    # Criar novo grupo
    new_group = {
        "name": "Teste",
        "description": "Grupo de teste criado via API"
    }
    response = requests.post(f"{BASE_URL}/groups", 
                           headers=headers, 
                           json=new_group)
    print(f"Status: {response.status_code}")
    print(f"Resposta: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    
    if response.status_code == 201:
        print("✅ Criação de grupo funcionando")
        group_id = response.json().get('group', {}).get('id')
        
        if group_id:
            print(f"\n4. Obtendo detalhes do grupo {group_id}...")
            response = requests.get(f"{BASE_URL}/groups/{group_id}", headers=headers)
            print(f"Status: {response.status_code}")
            print(f"Resposta: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
            
            if response.status_code == 200:
                print("✅ Obtenção de detalhes do grupo funcionando")
            else:
                print("❌ Erro ao obter detalhes do grupo")
    else:
        print("❌ Erro na criação de grupo")

if __name__ == "__main__":
    try:
        test_groups_api()
    except requests.exceptions.ConnectionError:
        print("❌ Erro: Não foi possível conectar ao servidor. Certifique-se de que o servidor está rodando em http://localhost:5000")
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
