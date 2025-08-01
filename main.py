import re
import requests
import json
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from pathlib import Path
import re
import html2text
import yt_dlp


def sanitize_filename(filename: str, max_length: int = 100) -> str:
    """
    Sanitize a filename for safe use on Windows filesystem.
    Preserves spaces and only replaces invalid characters with underscores.
    Handles reserved file names.
    
    Args:
        filename (str): The original filename
        max_length (int): Maximum length for the filename
        
    Returns:
        str: Sanitized filename safe for Windows
    """
    # Windows reserved file names (case-insensitive)
    reserved_names = {
        'CON', 'PRN', 'AUX', 'NUL',
        'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
        'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
    }
    
    # Replace invalid characters
    invalid_chars = r'[<>:"/\\|?*]'
    filename = re.sub(invalid_chars, '_', filename)
    
    # Remove leading/trailing spaces and dots
    filename = filename.strip(' .')
    
    # Only replace multiple consecutive underscores with a single one
    # Don't replace spaces with underscores
    filename = re.sub(r'_+', '_', filename)
    
    # Check if filename is a reserved name (case-insensitive)
    if filename.upper() in reserved_names:
        filename = f"_{filename}"
    
    # Handle length limit
    if len(filename) > max_length:
        filename = filename[:max_length].rstrip('_')
    
    # Ensure we have a valid filename
    if not filename:
        filename = "untitled"
    
    return filename


def download_video_with_ytdlp(video_type: int,video_id: str, output_path: Path, base_url: str) -> bool:
    """
    Download video using yt-dlp for Vimeo videos.
    
    Args:
        video_type (int): The type of video to download (7 = Vimeo, 4 = Youtube, 9 = Hyperlink)
        video_id (str): The video ID to download
        output_path (Path): Directory where to save the video
        base_url (str): Base URL for referer header
        
    Returns:
        bool: True if download successful, False otherwise
    """
    try:
        ydl_opts = {
            'outtmpl': str(output_path / f'Aula.%(ext)s'),
            'http_headers': {
                'Referer': base_url + '/',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            },
            'concurrent_fragment_downloads': 8,
            'quiet': False,
            'no_warnings': False,
            'retries': 3,
            'fragment_retries': 3,
        }
        if video_type == 7:
            video_url = f"https://player.vimeo.com/video/{video_id}"
        else:
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            ydl_opts['cookiesfrombrowser'] = ('vivaldi',)


        print(f"  + Tentando baixar: {video_url}")
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])

    except Exception as e:
        print(f"  - Erro ao baixar vídeo: {str(e)}")
        return False


def extract_nextjs_json_data(html_content: str) -> List[Dict[str, Any]]:
    """
    Extract JSON data from Next.js self.__next_f.push() calls in HTML content.
    Handles complex escaped JSON strings.
    
    Args:
        html_content (str): The HTML content containing script tags
        
    Returns:
        List[Dict[str, Any]]: List of extracted JSON objects
    """
    extracted_data = []
    
    patterns = [
        # Pattern 1: Basic format
        r'self\.__next_f\.push\(\[1,"([^"]+)"\]\)',
        # Pattern 2: More complex with nested quotes
        r'self\.__next_f\.push\(\[1,"(b:\[.*?\])"\]\)',
        # Pattern 3: Match the entire push call content
        r'self\.__next_f\.push\(\[(.*?)\]\)',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, html_content, re.DOTALL)
        
        for match in matches:
            try:
                if isinstance(match, str):
                    json_data = process_match_string(match)
                    if json_data:
                        extracted_data.extend(json_data)
                        
            except Exception as e:
                continue
    
    return extracted_data

def process_match_string(match_str: str) -> List[Dict[str, Any]]:
    """
    Process a matched string and extract JSON data from it.
    
    Args:
        match_str (str): The matched string from regex
        
    Returns:
        List[Dict[str, Any]]: List of extracted JSON objects
    """
    results = []
    
    approaches = [
        lambda s: process_b_format(s),
        lambda s: process_direct_json(s),
        lambda s: process_array_format(s),
    ]
    
    for approach in approaches:
        try:
            result = approach(match_str)
            if result:
                if isinstance(result, list):
                    results.extend(result)
                else:
                    results.append(result)
        except:
            continue
    
    return results

def process_b_format(s: str) -> Optional[Dict[str, Any]]:
    """Process strings that start with 'b:' format."""
    if s.startswith('b:'):
        json_content = s[2:]
        try:
            parsed = json.loads(json_content)
            if isinstance(parsed, list) and len(parsed) >= 4:
                return parsed[3]
        except:
            pass
    return None

def process_direct_json(s: str) -> Optional[Dict[str, Any]]:
    """Try to parse string directly as JSON."""
    try:
        return json.loads(s)
    except:
        return None

def process_array_format(s: str) -> Optional[Dict[str, Any]]:
    """Process array format like '1,"b:[...]"'."""
    try:
        array_data = json.loads(f'[{s}]')
        if len(array_data) >= 2:
            json_string = array_data[1]
            if isinstance(json_string, str) and json_string.startswith('b:'):
                return process_b_format(json_string)
    except:
        pass
    return None

def extract_with_manual_parsing(html_content: str) -> List[Dict[str, Any]]:
    """
    Manual parsing approach for heavily escaped content.
    """
    extracted_data = []
    
    script_pattern = r'<script[^>]*>(.*?self\.__next_f\.push.*?)</script>'
    script_matches = re.findall(script_pattern, html_content, re.DOTALL)
    
    for script_content in script_matches:
        push_pattern = r'self\.__next_f\.push\(\[([^\]]+)\]\)'
        push_matches = re.findall(push_pattern, script_content)
        
        for push_match in push_matches:
            try:
                array_str = f'[{push_match}]'

                parts_pattern = r'(\d+),"(b:\[.*\])"'
                parts_match = re.search(parts_pattern, push_match)
                
                if parts_match:
                    json_part = parts_match.group(2)
                    if json_part.startswith('b:'):
                        json_content = json_part[2:]
                        try:
                            parsed = json.loads(json_content)
                            if isinstance(parsed, list) and len(parsed) >= 4:
                                extracted_data.append(parsed[3])
                        except:
                            continue
                else:
                    try:
                        parsed_array = json.loads(array_str)
                        if len(parsed_array) >= 2:
                            json_string = parsed_array[1]
                            if isinstance(json_string, str) and json_string.startswith('b:'):
                                json_content = json_string[2:]
                                parsed = json.loads(json_content)
                                if isinstance(parsed, list) and len(parsed) >= 4:
                                    extracted_data.append(parsed[3])
                    except:
                        continue
                        
            except Exception as e:
                continue
    
    return extracted_data

def extract_course_data_specifically(html_content: str) -> Optional[Dict[str, Any]]:
    """
    Specifically extract course data, trying multiple approaches.
    """
    all_data = extract_nextjs_json_data(html_content)
    
    if not all_data:
        all_data = extract_with_manual_parsing(html_content)
    
    for data in all_data:
        if isinstance(data, dict):
            if 'slug' in data and 'content' in data:
                return data
            
            if 'content' in data and isinstance(data['content'], dict):
                content = data['content']
                if 'content' in content and isinstance(content['content'], dict):
                    inner_content = content['content']
                    if 'slug' in inner_content or 'title' in inner_content:
                        return data
    
    return None

def simplify_course_data(course_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simplify the course data structure to only include modules and their lessons.
    
    Args:
        course_data (Dict[str, Any]): The original complex course data
        
    Returns:
        Dict[str, Any]: Simplified course structure with only essential data
    """
    simplified = {
        "title": "",
        "slug": "",
        "modules": []
    }
    
    if 'content' in course_data and 'content' in course_data['content']:
        content = course_data['content']['content']
        simplified['title'] = content.get('title', 'Unknown')
        simplified['slug'] = content.get('slug', 'Unknown')
        
        if 'structure' in content:
            for item in content['structure']:
                if item.get('type') == 'MODULE' and 'data' in item:
                    module_data = item['data']
                    module = {
                        "id": module_data.get('id'),
                        "uuid": module_data.get('uuid'),
                        "title": module_data.get('title', ''),
                        "lessons": []
                    }
                    
                    if 'structure' in module_data:
                        for lesson_item in module_data['structure']:
                            if lesson_item.get('type') == 'LESSON' and 'data' in lesson_item:
                                lesson_data = lesson_item['data']
                                lesson = {
                                    "id": lesson_data.get('id'),
                                    "uuid": lesson_data.get('uuid'),
                                    "title": lesson_data.get('title', ''),
                                    "type": lesson_data.get('type'),
                                    "status": lesson_data.get('status', 'ACTIVE')
                                }
                                module['lessons'].append(lesson)
                    
                    simplified['modules'].append(module)
    
    return simplified

def debug_extraction(html_content: str, max_chars: int = 500) -> None:
    """
    Debug function to see what's being extracted.
    """
    print("=== DEBUG: Looking for script tags ===")
    
    # Find all script tags with self.__next_f.push
    script_pattern = r'<script[^>]*>(.*?self\.__next_f\.push.*?)</script>'
    script_matches = re.findall(script_pattern, html_content, re.DOTALL)
    
    print(f"Found {len(script_matches)} script tags with self.__next_f.push")
    
    for i, script_content in enumerate(script_matches):
        print(f"\n--- Script {i+1} ---")
        print(f"Content preview: {script_content[:max_chars]}...")
        
        # Look for push calls in this script
        push_pattern = r'self\.__next_f\.push\(\[([^\]]+)\]\)'
        push_matches = re.findall(push_pattern, script_content)
        
        print(f"Found {len(push_matches)} push calls")
        
        for j, push_match in enumerate(push_matches):
            print(f"  Push call {j+1}: {push_match[:200]}...")

session = requests.Session()


session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    })


print("🚀 === Kurseduka-dl ===")
print('Este é um aplicativo mínimo para download de cursos da plataforma Curseduca (https://curseduca.com/)')
print('Seu autor é o @katomaro (Telegram e Discord), seu guia de uso (altamente recomendado visitar) pode ser encontrado em: https://katomart.com/kursedu.html')
print('Lembrando, todos os aplicativos mínimos dispostos em katomart.com são melhor elaborados na suíte completa que está em construção.')
print('')
print('')
print('Para iniciarmos, você precisa informar a URL da plataforma da Curseduca (que é uma plataforma Whitelabel), sem informar nada adicional na url')
print('Exemplo para a URL base: https://portal.geoone.com.br')
print('Durante a execução, o programa irá até as URLs necessárias com base nessa url, por exemplo https://portal.geoone.com.br/login')
print('Lembre-se: Muito importante não incluir nada a mais na URL, inclusive barra final')
base_url = input('URL base: ')
cookie_domain = '.' + base_url.split('.', 1)[1]
login_url = f'{base_url}/login'


edu_watch_f_url = 'https://clas.curseduca.pro/bff/aulas/{lesson_uuid}/watch' 

auth_url = 'https://prof.curseduca.pro/login?redirectUrl='

username = input("Digite o seu usuário: ")
password = input("Digite a sua senha: ")


login_data = {
    'password': password,
    'username': username
}

response = session.get(login_url)
response.raise_for_status()

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:141.0) Gecko/20100101 Firefox/141.0',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'pt-BR,pt;q=0.8,en-US;q=0.5,en;q=0.3',
    'Origin': base_url,
    'Sec-GPC': '1',
    'Connection': 'keep-alive',
    'Referer': base_url + '/',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'cross-site',
    'Pragma': 'no-cache',
    'Cache-Control': 'no-cache',
}

api_key = session.get('https://application.curseduca.pro/platform-by-url', headers=headers)

api_key_val = api_key.json()['key']

temp_headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:141.0) Gecko/20100101 Firefox/141.0',
    'Accept': '*/*',
    'Accept-Language': 'pt-BR,pt;q=0.8,en-US;q=0.5,en;q=0.3',
    'Referer': base_url + '/',
    'api_key': api_key_val,
    'Content-Type': 'application/json',
    'Origin': base_url,
    'Connection': 'keep-alive',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'cross-site',
    'Priority': 'u=0',
    'Pragma': 'no-cache',
    'Cache-Control': 'no-cache',
}

response = session.post(auth_url, headers=temp_headers, json=login_data)
response.raise_for_status()

# {"accessToken": JWT,"refreshToken":UUID,"redirectUrl":"/courses","expiresAt":"2025-07-30TYY:MM:SS.XXXZ","authenticationId":INT,"currentLoginId":MD5/SHA,"member":{"isAdmin":false,"id":3687,"uuid":UUID,"name":STR,"email":USERNAME,"tenant":{"id":1,"uuid":UUID,"slug":"principal"}}}

auth_data = response.json()

# session.cookies.set('_ga', '', domain=cookie_domain)
# session.cookies.set('_ga_HK57WC3FTH', '', domain=cookie_domain)
session.cookies.set('access_token', auth_data.get('accessToken', ''), domain=cookie_domain)
session.cookies.set('admin-lang', 'pt_BR', domain=cookie_domain)
session.cookies.set('allow_tutorial', 'true', domain=cookie_domain)
session.cookies.set('api_key', api_key_val, domain=cookie_domain)
session.cookies.set('current_login_id', auth_data.get('currentLoginId', ''), domain=cookie_domain)
session.cookies.set('language', 'pt_BR', domain=cookie_domain)
session.cookies.set('language_tenant', '1', domain=cookie_domain)
session.cookies.set('platform_url', base_url, domain=cookie_domain)
session.cookies.set('tenant_slug', auth_data.get('member', {}).get('tenant', {}).get('slug', ''), domain=cookie_domain)
session.cookies.set('tenant_uuid', auth_data.get('member', {}).get('tenant', {}).get('uuid', ''), domain=cookie_domain)
session.cookies.set('tenantId', str(auth_data.get('member', {}).get('tenant', {}).get('id', '')), domain=cookie_domain)

user_data = {
    'id_prof_profile': auth_data.get('member', {}).get('id', ''),
    'nm_name': auth_data.get('member', {}).get('name', ''),
    'id_prof_authentication': auth_data.get('authenticationId', ''),
    'im_image': None,
    'nm_email': auth_data.get('member', {}).get('email', ''),
    'tenant_uuid': auth_data.get('member', {}).get('tenant', {}).get('uuid', ''),
    'slug_profile': f"{auth_data.get('member', {}).get('name', '').lower().replace(' ', '')}{auth_data.get('member', {}).get('id', '')}",
    'is_admin': auth_data.get('member', {}).get('isAdmin', False),
    'nm_headline': ''
}
session.cookies.set('user', json.dumps(user_data), domain=cookie_domain)
session.cookies.set('view', '2', domain=cookie_domain)

courses = []
page = 1
while True:
    params = {
        'redirect': '0',
        'limit': '100',
        'page': str(page)
    }
    course_page = session.get(base_url + '/restrita', params=params)
    soup = BeautifulSoup(course_page.text, 'html.parser')
    page_courses = []
    for card in soup.select('div.classified'):
        a = card.select_one('a.font-size-h4')
        if a and a.get('href'):
            name = a.get_text(strip=True)
            url = a['href']
            if not url.startswith('http'):
                url = base_url + url
            page_courses.append({'name': name, 'url': url})
    if not page_courses:
        break
    courses.extend(page_courses)
    page += 1


if not courses:
    print('Nenhum curso encontrado.')
    print(soup.prettify()[:2000])
    exit(1)

print('Cursos disponíveis:')
for idx, course in enumerate(courses, 1):
    print(f"{idx}. {course['name']}")

while True:
    try:
        choice = int(input('Selecione o número do curso desejado: '))
        if 1 <= choice <= len(courses):
            break
        else:
            print('Escolha inválida.')
    except ValueError:
        print('Por favor, digite um número válido.')

selected = courses[choice - 1]
course_response = session.get(selected['url'])
course_html = course_response.text
# debug_extraction(course_html)

course_data = extract_course_data_specifically(course_html)

if course_data:
    print("\n=== SUCCESSO EXTRAINDO CONTEUDO DO CURSO, BAIXANDO===")
    
    simplified_data = simplify_course_data(course_data)

    course_title = simplified_data.get('title', 'Nome Indeterminado')
    
    course_title = sanitize_filename(course_title)
    download_path = Path('downloads') / course_title
    
    download_path.mkdir(parents=True, exist_ok=True)
    print(f"Criado diretório: {download_path}")
    
    for module_index, module in enumerate(simplified_data['modules'], start=1):
        module_title = sanitize_filename(module['title'])
        print(f'Baixando módulo: {module_index} - {module_title}')
        module_path = download_path / f'{module_index}. {module_title}'
        module_path.mkdir(parents=True, exist_ok=True)
        
        for lesson_index, lesson in enumerate(module['lessons'], start=1):
            lesson_type = lesson.get('type')
            if lesson_type not in [4, 7]:
                print(f'Aula {lesson_index} - {lesson["title"]} não suportada por esta versão, envie uma issue no Github!\nSeu type e {lesson_type}')
                continue

            lesson_title = sanitize_filename(lesson['title'])
            print(f'Baixando aula: {lesson_index} - {lesson_title}')
            lesson_path = module_path / f'{lesson_index}. {lesson_title}'
            lesson_path.mkdir(parents=True, exist_ok=True)

            temp_headers['Authorization'] = f"Bearer {auth_data.get('accessToken', '')}"
            lesson_data = session.get(edu_watch_f_url.format(lesson_uuid=lesson['uuid']), headers=temp_headers)
            
            if lesson_data.status_code == 200:
                lesson_json = lesson_data.json()
                
                video_id = lesson_json.get('videoId')
                
                if video_id:
                    print(f"  + Video ID encontrado: {video_id}")
                    download_video_with_ytdlp(lesson_type, video_id, lesson_path, base_url)
                else:
                    print(f"  - Nenhum video ID encontrado para esta aula")
                
                description_html = lesson_json.get('description', '')
                if description_html:
                    h = html2text.HTML2Text()
                    h.ignore_links = False
                    h.ignore_images = False
                    h.body_width = 0
                    description_markdown = h.handle(description_html)
                    
                    description_file = lesson_path / "Descrição.txt"
                    with open(description_file, 'w', encoding='utf-8') as f:
                        f.write(description_markdown)
                    
                    print(f"  + Descrição salva em: {description_file}")
                else:
                    print(f"  - Nenhuma descrição encontrada para esta aula")

                
                if lesson_json.get('complementaries'):
                    print(f"  + Encontrados {len(lesson_json['complementaries'])} anexos")
                    for complementary in lesson_json['complementaries']:
                        file_id = complementary.get('id')
                        file_name = complementary.get('title', 'arquivo_complementar')
                        file_url = complementary.get('file', {}).get('url')
                        
                        if file_url:
                            print(f"    + Baixando: {file_name}")
                            try:
                                download_url = f"https://clas.curseduca.pro/lessons-complementaries/download?fileName={file_name}&fileUrl={file_url}&api_key={api_key_val}"
                                
                                download_headers = {
                                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:142.0) Gecko/20100101 Firefox/142.0',
                                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                                    'Accept-Language': 'pt-BR,pt;q=0.8,en-US;q=0.5,en;q=0.3',
                                    'Connection': 'keep-alive',
                                    'Referer': base_url + '/',
                                    'Upgrade-Insecure-Requests': '1',
                                    'Sec-Fetch-Dest': 'document',
                                    'Sec-Fetch-Mode': 'navigate',
                                    'Sec-Fetch-Site': 'cross-site',
                                    'Sec-Fetch-User': '?1',
                                    'Priority': 'u=0, i',
                                    'Pragma': 'no-cache',
                                    'Cache-Control': 'no-cache',
                                }
                                
                                response = session.get(download_url, headers=download_headers)
                                if response.status_code == 200:
                                    file_path = lesson_path / file_name
                                    with open(file_path, 'wb') as f:
                                        f.write(response.content)
                                    print(f"    + Arquivo salvo: {file_path}")
                                else:
                                    print(f"    - Erro ao baixar {file_name}: {response.status_code}")
                            except Exception as e:
                                print(f"    - Erro ao baixar {file_name}: {e}")
                        else:
                            print(f"    - URL não encontrada para {file_name}")
            else:
                print(f"  - Erro ao obter dados da aula: {lesson_data.status_code}")
else:
    print("Nao foi possivel extrair os dados do curso")
