FROM nginxinc/nginx-unprivileged:alpine
COPY infra/nginx/development.conf /etc/nginx/conf.d/corna.nginx.conf

COPY frontend/public /www/static
COPY themes/ /themes/static
