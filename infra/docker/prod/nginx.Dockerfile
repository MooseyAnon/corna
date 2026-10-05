FROM nginxinc/nginx-unprivileged:alpine
COPY infra/nginx/production.conf /etc/nginx/conf.d/corna.nginx.conf

COPY frontend/public /www/static
COPY themes/ /themes/static
