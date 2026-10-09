FROM nginxinc/nginx-unprivileged:alpine
COPY infra/nginx/snippets/block-suspicious-paths.conf /etc/nginx/snippets/block-suspicious-paths.conf
COPY infra/nginx/production.conf /etc/nginx/conf.d/corna.nginx.conf

COPY frontend/public /www/static
COPY themes/ /themes/static
