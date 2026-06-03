FROM mirror2.chabokan.net/nginx:latest
COPY templates/index.html /usr/share/nginx/html/index.html
COPY templates/letter.html /usr/share/nginx/html/letter.html
COPY templates/risk.html /usr/share/nginx/html/risk.html
COPY templates/ingest.html /usr/share/nginx/html/ingest.html
COPY static/ /usr/share/nginx/html/static/
COPY nginx-ui.conf /etc/nginx/conf.d/default.conf
EXPOSE 3000
