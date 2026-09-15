# Guia Completo — VM + Preparação + Auto-avaliação do Inception

Este guia está dividido em 3 partes:

1. **Parte A** — Criar a Máquina Virtual no Linux (app "Boxes" / VirtualBox)
2. **Parte B** — Preparar o projeto dentro da VM para seguir a avaliação na perfeição
3. **Parte C** — Passo a passo de teste, replicando exatamente o que o teu avaliador vai fazer (com base no PDF `Intra_Projects_Inception_Edit.pdf`)

Sempre que vires `<login>`, substitui pelo teu login 42 real (ex: `dasantos`).

---

## PARTE A — Criar a Virtual Machine no Linux

O 42 recomenda que o projeto corra **dentro de uma VM** (não diretamente no host). Nos campus 42 (Fedora), a aplicação mais comum é o **GNOME Boxes** ("Caixas"). Se estiveres noutra distro, o **VirtualBox** é a alternativa universal. Escolhe uma das duas opções abaixo.

### Opção 1 — GNOME Boxes (recomendado nos PCs 42/Fedora)

1. **Abrir a aplicação**
   - Procura por "Boxes" (ou "Caixas") no menu de aplicações e abre-a.

2. **Descarregar uma imagem Debian**
   - Vai a https://www.debian.org/download e copia o link do `.iso` da versão **estável** (não "testing"/"unstable").
   - Ou, dentro do Boxes, clica em **"+" → "Criar Máquina Virtual"** e escolhe a opção de descarregar um SO diretamente da lista (o Boxes tem uma galeria com Debian/Fedora prontos a descarregar).

3. **Criar a VM**
   - Clica no botão **"+"** (canto superior esquerdo) → **"Create a Virtual Machine"**.
   - Escolhe **"Operating System Download"** e procura "Debian", ou seleciona o `.iso` que descarregaste manualmente ("Operating System Image File").
   - Define os recursos:
     - **RAM**: pelo menos 2–4 GB (idealmente 4 GB se o PC permitir).
     - **Disco**: pelo menos 20–25 GB (Docker + imagens + WordPress ocupam espaço).
     - **CPUs**: 2, se possível.
   - Clica em **"Create"**.

4. **Instalar o Debian dentro da VM**
   - Segue o instalador gráfico normal do Debian: idioma, teclado, criação de utilizador (`<login>` ou outro nome à tua escolha), password, partição de disco automática ("guided - use entire disk").
   - No ecrã de seleção de software, garante que fica marcado **"SSH server"** e **"standard system utilities"** (não precisas de ambiente gráfico dentro da VM — server puro é suficiente e mais leve).
   - Termina a instalação e reinicia.

5. **Aceder à VM**
   - Depois de instalada, a VM aparece na lista do Boxes — basta dar duplo-clique para abrir a janela do terminal/ecrã da VM.
   - (Opcional, mais confortável) Ativa a rede em modo *bridge* nas definições da VM para conseguires fazer SSH a partir do teu terminal normal em vez de usares só a janela do Boxes.

### Opção 2 — VirtualBox

1. Instala o VirtualBox no host (se ainda não tiveres):
   ```bash
   sudo apt update && sudo apt install virtualbox
   ```
2. Descarrega a ISO do Debian estável: https://www.debian.org/download
3. Abre o VirtualBox → **"New"**:
   - Nome: `inception-vm`, Type: Linux, Version: Debian (64-bit).
   - RAM: 4096 MB. Disco: 25 GB (dinâmico).
4. Nas definições da VM → **Storage** → adiciona a ISO do Debian na drive ótica.
5. Nas definições da VM → **Network** → Adapter 1 → **"Bridged Adapter"** (para a VM ter o seu próprio IP na rede, facilitando testes de `login.42.fr` a partir do host).
6. Inicia a VM e instala o Debian normalmente (mesmo processo do passo 4 da Opção 1).

### Depois de instalado (qualquer uma das opções): preparar o sistema

Liga-te à VM (terminal da própria janela, ou via SSH) e corre:

```bash
# Atualizar o sistema
sudo apt update && sudo apt full-upgrade -y

# Ferramentas base
sudo apt install -y curl git make ca-certificates gnupg lsb-release

# --- Instalar Docker Engine + Docker Compose plugin (repositório oficial) ---
curl -fsSL https://download.docker.com/linux/debian/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Permitir correr docker sem sudo (faz logout/login depois, ou reinicia a VM)
sudo usermod -aG docker $USER

# Confirmar instalação
docker --version
docker compose version
make --version
```

Reinicia a VM (ou faz logout/login) para o grupo `docker` fazer efeito:

```bash
sudo reboot
```

---

## PARTE B — Preparar o projeto dentro da VM

### 1. Copiar/clonar o projeto para dentro da VM

Se já tens o teu repositório Git configurado (ex: no vogsphere.42porto.com), o mais correto é **clonar diretamente dentro da VM**, tal como o avaliador vai fazer:

```bash
cd ~
git clone git@vogsphere.42porto.com:vogsphere/intra-uuid-XXXXXXXX.git inception
cd inception
```

Se ainda estás a preparar o projeto localmente (como o zip que te dei), copia os ficheiros para dentro do repositório git e faz commit/push a partir da VM, ou usa `scp`/pasta partilhada para transferir o zip para a VM e depois `git init` + `git add` + `git commit` + `git push` lá dentro.

> **Importante**: o avaliador vai clonar o teu repositório **numa pasta vazia**. Testa exatamente esse cenário antes de entregar (ver Parte C, passo 0).

### 2. Ajustar o login em todo o lado

Substitui `yourlogin` pelo teu login 42 real em **dois ficheiros**:

```bash
# No Makefile
sed -i 's/yourlogin/<login>/' Makefile

# No srcs/.env
sed -i 's/yourlogin/<login>/g' srcs/.env
```

Confirma:

```bash
grep LOGIN Makefile srcs/.env
grep DOMAIN_NAME srcs/.env
```

### 3. Gerar passwords reais nos secrets

Os ficheiros em `secrets/` vêm com passwords geradas aleatoriamente só para o projeto arrancar "out of the box" — troca-as por passwords tuas antes da entrega (nunca commits a password óbvia tipo "1234"):

```bash
cd secrets
echo "$(openssl rand -base64 24)" > db_password.txt
echo "$(openssl rand -base64 24)" > db_root_password.txt
echo "$(openssl rand -base64 24)" > credentials.txt        # password do admin WP
echo "$(openssl rand -base64 24)" > wp_user_password.txt   # password do 2º user WP
cd ..
```

Confirma que o `.gitignore` está a ignorar corretamente estes ficheiros (crucial — credenciais no git = nota 0 na avaliação):

```bash
git status
# secrets/*.txt e srcs/.env NÃO devem aparecer como "untracked"/"to be committed"
git check-ignore -v secrets/db_password.txt srcs/.env
```

### 4. Configurar o nome de domínio (`/etc/hosts`)

Dentro da VM:

```bash
echo "127.0.0.1  <login>.42.fr" | sudo tee -a /etc/hosts
```

Se vais também aceder ao site a partir do **host** (fora da VM), no host faz o mesmo apontando para o IP da VM (não para `127.0.0.1`):

```bash
# no HOST, não na VM — substitui pelo IP real da VM (ip a | grep inet, dentro da VM)
echo "<IP_DA_VM>  <login>.42.fr" | sudo tee -a /etc/hosts
```

### 5. Rever o nome do username admin do WordPress

A grelha de avaliação é **estrita** quanto a isto: o username do admin não pode conter `admin`/`Admin`/`administrator`/`Administrator`, nem combinações como `admin-123`. No `srcs/.env` já está definido `WP_ADMIN_USER=supervisor_le` — confirma que continua conforme e ajusta se quiseres:

```bash
grep WP_ADMIN_USER srcs/.env
```

### 6. Primeiro arranque de teste

```bash
make
make ps
```

Devias ver `nginx`, `wordpress` e `mariadb` todos `Up`. Se algo falhar, corre `make logs` e lê o erro antes de continuar.

---

## PARTE C — Passo a passo de teste (simula exatamente o avaliador)

Esta parte segue **ponto por ponto** o PDF da grelha de avaliação que enviaste. Corre isto tu mesmo, sozinho, antes da defesa — se passares em tudo aqui, a avaliação real corre bem.

### Passo 0 — Simular um "clone limpo" (recomendado)

```bash
cd ~
rm -rf inception_test
git clone <URL_DO_TEU_REPO> inception_test
cd inception_test
ls -la
# Confirma: existe Makefile na raiz, existe pasta srcs/ na raiz,
# existe README.md, USER_DOC.md, DEV_DOC.md na raiz.
```

Se faltar algum destes, a avaliação **termina automaticamente com nota 0** — corrige antes de continuar.

⚠️ Repara: um clone limpo **não traz a pasta `secrets/`** se estiver no `.gitignore` (como deve estar). Isto é esperado — a pasta `secrets/` é normalmente entregue "à mão" durante a avaliação (recriada localmente), ou fica fora do `.gitignore` mas sem conter passwords reais/sensíveis publicamente expostas — confirma com o teu staff/pedagogia local qual é a prática aceite no teu campus (nalguns campus a pasta `secrets/` com ficheiros vazios/placeholder fica no repo, só o **conteúdo real** é que não pode estar; noutros, cria-se localmente antes da avaliação). Para seres seguro, tem sempre os 4 ficheiros de `secrets/` prontos para recriar em segundos:

```bash
mkdir -p secrets
echo "SenhaForte123!" > secrets/db_password.txt
echo "SenhaForte456!" > secrets/db_root_password.txt
echo "SenhaForte789!" > secrets/credentials.txt
echo "SenhaForte000!" > secrets/wp_user_password.txt
```

### Passo 1 — Limpar tudo (exatamente o comando do avaliador)

```bash
docker stop $(docker ps -qa) 2>/dev/null
docker rm $(docker ps -qa) 2>/dev/null
docker rmi -f $(docker images -qa) 2>/dev/null
docker volume rm $(docker volume ls -q) 2>/dev/null
docker network rm $(docker network ls -q) 2>/dev/null
sudo rm -rf /home/<login>/data/*
```

### Passo 2 — Verificações estáticas nos ficheiros (antes de correr nada)

```bash
# Sem 'network: host' nem 'links:'
grep -nE "network:\s*host|links:" srcs/docker-compose.yml && echo "❌ ENCONTRADO — corrigir!" || echo "✅ OK"

# Deve haver uma secção 'networks:'
grep -n "networks:" srcs/docker-compose.yml && echo "✅ OK"

# Sem '--link' em Makefile/scripts
grep -rn -- "--link" Makefile srcs/ && echo "❌ ENCONTRADO — corrigir!" || echo "✅ OK"

# Sem 'tail -f', 'sleep infinity', 'while true', 'bash'/'sh' soltos em ENTRYPOINT
grep -rn "tail -f\|sleep infinity\|while true" srcs/requirements/*/Dockerfile srcs/requirements/*/tools/*.sh && echo "❌ ENCONTRADO — corrigir!" || echo "✅ OK"
grep -n "ENTRYPOINT" srcs/requirements/*/Dockerfile

# Todas as Dockerfiles começam com FROM debian:<versão> ou FROM alpine:<versão> (nunca 'latest')
grep -n "^FROM" srcs/requirements/*/Dockerfile
```

Nos meus ficheiros deves ver `FROM debian:bookworm-slim` nas três — confirma que `bookworm` é de facto a penúltima versão estável no momento da tua avaliação (a Debian lança novas versões de tempos a tempos — vale a pena confirmar em https://www.debian.org/releases/ pouco antes de entregar, e ajustar se entretanto tiver saído uma nova versão estável).

### Passo 3 — Correr o Makefile

```bash
make
```

Não deve haver crashes. Confirma:

```bash
docker compose -f srcs/docker-compose.yml ps
```

As 3 imagens devem chamar-se **exatamente** `mariadb`, `wordpress`, `nginx` (mesmo nome do serviço):

```bash
docker images
```

### Passo 4 — Testar a rede Docker

```bash
docker network ls
# Deve aparecer uma rede chamada algo como "inception_inception" ou "srcs_inception"
```

Prepara também uma explicação simples (vais ter de a dar oralmente):
> *"O docker-network cria uma rede privada partilhada só pelos meus 3 containers. Dentro dela, cada container consegue chamar os outros pelo nome do serviço (ex: `wordpress` chama `mariadb` por `mysqladmin ping -h mariadb`), sem expor essas portas ao exterior. Só a porta 443 do nginx é publicada para fora, para o host."*

### Passo 5 — Testar o acesso via HTTPS (porta 443) e bloqueio de HTTP

```bash
# Isto DEVE falhar / não ligar (porta 80 não está publicada)
curl -v http://<login>.42.fr 2>&1 | head -20

# Isto DEVE funcionar (aceita o certificado self-signed com -k)
curl -vk https://<login>.42.fr 2>&1 | head -40
```

No output do segundo comando, confirma que aparece `SSL connection using TLSv1.2` ou `TLSv1.3` — nunca deve permitir TLSv1.0/1.1.

Abre também no browser: `https://<login>.42.fr` — deve dar aviso de certificado não confiável (normal, é self-signed), aceita e avança. **Não deve aparecer o assistente de instalação do WordPress** — se aparecer, algo falhou na instalação automática (ver `docker compose logs wordpress`).

### Passo 6 — Dockerfiles: verificação individual

```bash
for s in mariadb nginx wordpress; do
  echo "--- $s ---"
  test -s srcs/requirements/$s/Dockerfile && echo "✅ Dockerfile existe e não está vazio" || echo "❌ FALTA/VAZIO"
  grep -qi nginx srcs/requirements/$s/Dockerfile && [ "$s" != "nginx" ] && echo "❌ nginx dentro do Dockerfile de $s!" 
done
```

### Passo 7 — Volumes (o comando exato que o avaliador vai usar)

```bash
docker volume ls
# copia o nome exato dos dois volumes (ex: srcs_db_data, srcs_wp_data)

docker volume inspect srcs_db_data | grep Mountpoint
docker volume inspect srcs_wp_data | grep Mountpoint
```

Ambos devem mostrar um caminho a começar por `/home/<login>/data/`. Se mostrarem outra coisa (ex: `/var/lib/docker/volumes/...`), o `driver_opts` do `docker-compose.yml` não está a funcionar — revê o `LOGIN` no `srcs/.env`.

### Passo 8 — WordPress: comentário como user + login como admin + editar página

```bash
docker compose -f srcs/docker-compose.yml exec wordpress wp user list --path=/var/www/html --allow-root
```

Confirma que aparecem **pelo menos 2 utilizadores**, um deles administrador (username sem "admin"/"administrator").

No browser:
1. Vai a `https://<login>.42.fr` → adiciona um comentário num artigo com o utilizador secundário (podes ter de ativar comentários / usar o utilizador secundário para publicar um artigo de teste primeiro, se preferires).
2. Vai a `https://<login>.42.fr/wp-admin` → entra com o **admin** (username em `srcs/.env` → `WP_ADMIN_USER`, password em `secrets/credentials.txt`).
3. Edita uma página existente (ex: muda o texto da página "Sample Page" ou da homepage).
4. Volta a `https://<login>.42.fr` (fora do admin) e confirma que a alteração aparece.

### Passo 9 — MariaDB: login e confirmar que não está vazia

```bash
DB_PASS=$(cat secrets/db_password.txt)
docker compose -f srcs/docker-compose.yml exec mariadb mysql -u wp_user -p"$DB_PASS" wordpress -e "SHOW TABLES;"
```

Deve listar as tabelas típicas do WordPress (`wp_posts`, `wp_users`, `wp_options`, etc). Prepara a explicação oral:
> *"Entro com `mysql -u <user> -p` dentro do container mariadb, uso a password guardada em `secrets/db_password.txt`, e seleciono a base `wordpress` criada no arranque."*

### Passo 10 — Persistência (reboot da VM)

```bash
sudo reboot
```

Depois de a VM reiniciar:

```bash
cd ~/inception   # ou inception_test, conforme o teste
make
```

Espera todos os containers ficarem `Up` de novo, depois confirma:
- `https://<login>.42.fr` continua a funcionar.
- A página que editaste no Passo 8 continua editada.
- O comentário que adicionaste continua lá.
- `docker compose exec mariadb mysql ...` continua a mostrar os mesmos dados.

Se algo se perdeu, o volume não está mesmo persistente — revê o Passo 7.

### Passo 11 — Modificação de configuração ao vivo (simulação da defesa)

O avaliador vai pedir para mudares a porta de **um** serviço, à escolha dele. Treina os 3 cenários possíveis:

```bash
# Exemplo: mudar a porta do nginx de 443 para 8443
sed -i 's/^NGINX_PORT=.*/NGINX_PORT=8443/' srcs/.env
make re
curl -vk https://<login>.42.fr:8443 2>&1 | head -20   # deve funcionar
curl -vk https://<login>.42.fr 2>&1 | head -5          # já não deve responder na 443

# repõe para 443 antes de continuares a testar outras coisas
sed -i 's/^NGINX_PORT=.*/NGINX_PORT=443/' srcs/.env
make re
```

```bash
# Exemplo: mudar a porta do php-fpm de 9000 para 9001
sed -i 's/^WP_FPM_PORT=.*/WP_FPM_PORT=9001/' srcs/.env
make re
docker compose -f srcs/docker-compose.yml ps    # confirma "Up" em wordpress e nginx
curl -vk https://<login>.42.fr 2>&1 | head -10  # o site deve continuar a funcionar
```

```bash
# Exemplo: mudar a porta do MariaDB de 3306 para 3307
sed -i 's/^DB_PORT=.*/DB_PORT=3307/' srcs/.env
make re
docker compose -f srcs/docker-compose.yml logs wordpress | tail -20   # sem erros de ligação à BD
```

Depois de treinares os 3, repõe os valores por defeito (443 / 9000 / 3306) antes da avaliação real, para começares limpo.

### Passo 12 — Preparar as respostas teóricas (vão-te ser pedidas)

Tem estas 4 respostas prontas, curtas e claras:

1. **Como funcionam Docker e docker compose**: Docker cria containers — processos isolados que partilham o kernel do host mas têm o seu próprio sistema de ficheiros, rede e dependências, definidos num Dockerfile e "compilados" numa imagem. O `docker compose` orquestra vários containers relacionados (definidos num `docker-compose.yml`) como um único stack: cria a rede partilhada, os volumes, resolve a ordem de arranque (`depends_on`) e gere todos com um único comando.

2. **Imagem Docker com vs. sem docker compose**: A imagem em si é idêntica nos dois casos — o que muda é como o container é criado a partir dela. Sem compose, teria de correr manualmente `docker network create`, `docker volume create`, e um `docker run` gigante com todas as flags (`-v`, `--network`, `-e`, `-p`...) para cada serviço, repetido sempre que precisasse de recriar. Com compose, tudo isso fica declarado uma vez em YAML e reproduz-se com um único `docker compose up`.

3. **Vantagem do Docker face a VMs**: uma VM virtualiza hardware completo (incluindo o seu próprio kernel), o que a torna pesada e lenta a arrancar. Um container Docker partilha o kernel do host e só isola processo/rede/filesystem, por isso arranca em segundos, usa muito menos RAM/CPU/disco, e as imagens são fáceis de partilhar e reproduzir de forma idêntica em qualquer máquina.

4. **Pertinência da estrutura de pastas**: `srcs/` agrupa tudo o que é necessário para configurar a app (compose + Dockerfiles), separado dos `secrets/` (nunca deve ir para o repo com dados reais) e do `Makefile` na raiz (ponto de entrada único). Dentro de `srcs/requirements/`, cada serviço tem a sua própria pasta com o seu Dockerfile, `conf/` e `tools/` — isto isola claramente a responsabilidade de cada serviço e facilita adicionar novos (como os bonus) sem misturar código.

### Checklist final antes de entregar

- [ ] `git clone` numa pasta vazia mostra `Makefile`, `srcs/`, `README.md`, `USER_DOC.md`, `DEV_DOC.md` na raiz
- [ ] Primeira linha do `README.md` é itálico: `*This project has been created as part of the 42 curriculum by <login>.*`
- [ ] `README.md` tem secções Description / Instructions / Resources (com explicação do uso de IA)
- [ ] `USER_DOC.md` e `DEV_DOC.md` existem e não estão vazios
- [ ] Nenhuma password/API key no git fora de `secrets/` (confirmado com `git log -p | grep -i pass` no histórico todo, não só no estado atual)
- [ ] `docker-compose.yml` sem `network: host` nem `links:`, com `networks:` definido
- [ ] Nenhum `--link`, `tail -f`, `sleep infinity`, `while true`, `bash`/`sh` sozinho em nenhum ENTRYPOINT/script
- [ ] As 3 Dockerfiles começam por `FROM debian:<versão-penúltima-estável>` (ou alpine equivalente), nunca `latest`
- [ ] Nomes das imagens = nomes dos serviços (`mariadb`, `wordpress`, `nginx`)
- [ ] `http://<login>.42.fr` não responde; `https://<login>.42.fr` responde com TLSv1.2/1.3
- [ ] WordPress já instalado (sem assistente de instalação visível)
- [ ] Admin username sem "admin"/"administrator" em nenhuma forma
- [ ] `docker volume inspect` mostra `/home/<login>/data/...` nos dois volumes
- [ ] Comentário como user + edição de página como admin, ambos refletidos no site
- [ ] Dados sobrevivem a `sudo reboot` + `make`
- [ ] Testaste mudar a porta de cada um dos 3 serviços via `.env` + `make re`, e voltou tudo ao normal (443/9000/3306) antes da entrega
- [ ] (Se fores fazer bonus) mandatory 100% perfeito primeiro — bonus só conta se o resto estiver impecável
