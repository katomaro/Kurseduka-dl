# Kurseduka-dl

Aplicativo mínimo para download de cursos da plataforma Curseduca. Uma versão mais robusta se encontrará no [Katomart](https://github.com/katomaro/katomart)

## Descrição

Este é um script Python que permite baixar cursos da plataforma Whitelabel Curseduca (https://curseduca.com/). O aplicativo extrai automaticamente a estrutura do curso, incluindo módulos, aulas e materiais complementares.

## Funcionalidades

- Autenticação automática na plataforma
- Extração da estrutura completa do curso
- Download de vídeos (Vimeo e YouTube, os demais precisam ser descobertos, abra issue)
- Download de materiais complementares
- Organização automática em pastas por módulo e aula
- Sanitização de nomes de arquivos para compatibilidade com Windows

## Requisitos

- Python 3.12+
- Dependências listadas em `requirements.txt`

## Instalação

### Pré-requisitos do Sistema

- **Navegador Vivaldi**: Necessário para autenticação com YouTube caso a maior parte dos seus vídeos estejam no Youtube, ou você esteja usando vpn/proxy
- **FFmpeg**: Preferencialmente instalado no PATH do sistema para melhor compatibilidade de vídeo

### Opção 1: Release (Recomendado)

Para usuários Windows e Linux, baixe a release mais recente na aba [Releases](https://github.com/katomaro/kurseduka-dl/releases) deste repositório.

### Opção 2: Executando da Fonte (MacOS/Devs)

1. Clone este repositório
2. Crie um ambiente virtual:
   ```
   python -m venv venv
   ```
3. Ative o ambiente virtual:
   - Windows: `venv\Scripts\activate`
   - Linux/Mac: `source venv/bin/activate`
4. Instale as dependências:
   ```
   pip install -r requirements.txt
   ```

## Uso

Execute o script principal:
```
python main.py
```

O programa solicitará:
- URL base da plataforma (ex: https://portal.geoone.com.br)
- Usuário e senha da conta
- Seleção do curso desejado

Os arquivos serão baixados na pasta `downloads/` organizados por curso, módulo e aula.

## Limitações

Guia de uso e avisos quanto a plataforma QUE NÃO É SEGURA em sua página do site [Katomart](https://katomart.com/kursedu.html)

## Licença

Toda, pode passar.
