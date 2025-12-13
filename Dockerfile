# 1. Usamos uma imagem base leve e oficial do Python
FROM python:3.10-slim

# 2. Define variáveis de ambiente para otimizar o Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 3. Define o diretório de trabalho dentro do container
WORKDIR /app

# 4. Instala dependências do sistema operacional necessárias
# (gcc e libpq-dev são úteis se você usar bancos de dados no futuro)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 5. Copia e instala as dependências do Python
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 6. Copia todo o resto do código para dentro do container
COPY . .

# 7. Segurança: Cria um usuário não-root para rodar a aplicação
# (Rodar como root é uma falha de segurança comum que evitamos no Padrão Ouro)
RUN useradd -m appuser
USER appuser

# 8. Comando para iniciar o servidor Gunicorn
# O Render injeta a variável $PORT automaticamente
CMD gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 60