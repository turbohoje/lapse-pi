  docker build -t temper-scraper ./temper                                                                                                                                      
                                                                                                                                                                               
  docker run -d \                                                                                                                                                              
    --name temper-scraper \                                                                                                                                                    
    --restart unless-stopped \                                                                                                                                                 
    --privileged \                                                                                                                                                             
    -v /sys:/sys:ro \
    --env-file ./temper/.env \                                                                                                                                                 
    temper-scraper
