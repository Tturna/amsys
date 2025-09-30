AMSYS is a software provisioning platform designed to make simple database application management easy. It was designed to provide 3rd parties dynamic access to in-house services without the need to expose
in-house data or operations, while still providing the option to connect data between users.

### Highlighted features:
- Create and manage app instances using merely a couple intuitive buttons and web forms
  - Automatic Docker container management with Bash and Docker SDK for Python
  - Automatic dynamic routing using Traefik proxy
- Logical management of data transfer connections between instances
  - Automatic SSH certificate authentication and API communication between instances
- Automatic creation of a map view with visualized data connections based on defined app locations
  - Map made with LeafletJS
- Intuitive web interface with user authentication and authorization

### Used tools include:
- Python
- Django
- SQLite
- Docker (and Docker SDK for Python)
- Traefik
- OpenSSH
- Linux

This project was done for a company whose systems were Azure based. This system was hosted in a VM in the cloud using Azure Application Gateway.

### Interface screenshots
![Main interface](https://github.com/Tturna/amsys/blob/main/dashboard/img/ss-amsys-main.png?raw=true)
![Main interface](https://github.com/Tturna/amsys/blob/main/dashboard/img/ss-amsys-map.png?raw=true)
