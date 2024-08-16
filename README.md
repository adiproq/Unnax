### Docker Build
docker build -t creditwave-unnax . 

### Docker Run
docker run -p 5000:5000 creditwave-unnax

### Create HTTPS Ngrok
ngrok http 5000