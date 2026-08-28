# Glosario de Acrónimos del SOAR Ransomware Lab

Este documento define los acrónimos y términos técnicos que se usan en toda la documentación del proyecto. Se recomienda mantenerlo como referencia central y consultarlo antes de introducir nuevos términos en guías, manuales o memoria académica.

## Abreviaturas Técnicas

| Abreviatura | Término Completo                                |
|-------------|-------------------------------------------------|
| **AES**     | Advanced Encryption Standard (Estándar de Cifrado Avanzado) — cifrado simétrico usado en blobs C2 de Pulsar RAT |
| **API**     | Application Programming Interface               |
| **AV**      | Antivirus                                       |
| **CACAO**   | Collaborative Automated Course of Action Operations (estándar OASIS para playbooks de seguridad) |
| **CI/CD**   | Continuous Integration / Continuous Deployment  |
| **CIS**     | Center for Internet Security (Centro para la Seguridad de Internet) — benchmarks y controles CIS |
| **CLI**     | Command Line Interface (Interfaz de Línea de Comandos) |
| **CPU**     | Central Processing Unit                         |
| **CSV**     | Comma-Separated Values                          |
| **DLL**     | Dynamic-Link Library (Biblioteca de Enlace Dinámico) — componentes Windows cargados por TREZ_cor |
| **DNS**     | Domain Name System (Sistema de Nombres de Dominio) |
| **Docker**  | Plataforma de contenerización                   |
| **E2E**     | End-to-End (Extremo a Extremo) — pruebas sobre el flujo completo de alerta |
| **EDR**     | Endpoint Detection and Response                 |
| **ENISA**   | European Union Agency for Cybersecurity (Agencia de Ciberseguridad de la UE) |
| **ES**      | Elasticsearch — motor de búsqueda y análisis; índices `soar-alerts` y `soar-metrics` |
| **GCM**     | Galois/Counter Mode (modo de cifrado autenticado AES-GCM usado en config C2 de Pulsar RAT) |
| **HTTP**    | Hypertext Transfer Protocol                     |
| **HTTPS**   | Hypertext Transfer Protocol Secure              |
| **HVNC**    | Hidden Virtual Network Computing (escritorio virtual oculto usado por Pulsar RAT) |
| **IaaS**    | Infrastructure as a Service                     |
| **IEC**     | International Electrotechnical Commission (Comisión Electrotécnica Internacional) — coautora de ISO/IEC 27001 |
| **IETF**    | Internet Engineering Task Force — organización que publica RFCs |
| **IoC**     | Indicator of Compromise (Indicador de Compromiso) — hashes, IPs, dominios analizados por Cortex/MISP |
| **IP**      | Internet Protocol                               |
| **IR**      | Incident Response (Respuesta a Incidentes)      |
| **JSON**    | JavaScript Object Notation                      |
| **KB**      | Kilobyte                                        |
| **KPI**     | Key Performance Indicator (Indicador Clave de Rendimiento), p. ej. MTTR |
| **MB**      | Megabyte                                        |
| **MTTR**    | Mean Time to Respond (Tiempo Medio de Respuesta) |
| **OS**      | Operating System                                |
| **PDF**     | Portable Document Format                        |
| **PYME**    | Pequeña y Mediana Empresa                       |
| **RAM**     | Random Access Memory                            |
| **RaaS**    | Ransomware as a Service                         |
| **RAR**     | Roshal Archive (formato de compresión usado por GMinst4ll para empaquetado anidado) |
| **REST**    | Representational State Transfer                 |
| **RF**      | Requisito Funcional (Functional Requirement)    |
| **RFC**     | Request for Comments (estándares técnicos publicados por IETF) |
| **RNF**     | Requisito No Funcional (Non-Functional Requirement) |
| **ROI**     | Return on Investment                            |
| **SANS**    | SysAdmin, Audit, Network, Security — instituto de investigación de ciberseguridad (DShield) |
| **SHA256**  | Secure Hash Algorithm 256-bit (algoritmo de hash usado para fingerprints de malware) |
| **Sigma**   | Formato genérico de reglas de detección para SIEM |
| **SIRP**    | Security Incident Response Playbook (playbook de respuesta a incidentes) |
| **SIEM**    | Security Information and Event Management       |
| **SLA**     | Service Level Agreement                         |
| **SMART**   | Specific, Measurable, Achievable, Relevant, Time-bound (criterios para objetivos) |
| **SOAR**    | Security Orchestration, Automation and Response |
| **SQL**     | Structured Query Language                       |
| **SSD**     | Solid State Drive                               |
| **SSH**     | Secure Shell                                    |
| **SSL**     | Secure Sockets Layer                            |
| **TLS**     | Transport Layer Security                        |
| **TFM**     | Trabajo Fin de Máster                           |
| **UI**      | User Interface                                  |
| **URL**     | Uniform Resource Locator                        |
| **VBS**     | Visual Basic Script (VBScript) — scripts de persistencia usados por GMinst4ll |
| **VM**      | Virtual Machine                                 |
| **XDR**     | Extended Detection and Response                 |
| **YARA**    | Yet Another Ridiculous Acronym — lenguaje de reglas para identificación de malware |
| **JWT**     | JSON Web Token (Token Web JSON) — autenticación HS256 en la API |
| **SOC**     | Security Operations Center (Centro de Operaciones de Seguridad) |
| **CSIRT**   | Computer Security Incident Response Team (Equipo de Respuesta a Incidentes) |
| **CERT**    | Computer Emergency Response Team                 |
| **MTTD**    | Mean Time to Detect (Tiempo Medio de Detección)  |
| **NIST**    | National Institute of Standards and Technology   |
| **ISO**     | International Organization for Standardization   |
| **GDPR**    | General Data Protection Regulation (Reglamento General de Protección de Datos) |
| **MITRE**   | MITRE Corporation — organización que mantiene ATT&CK |
| **ATT&CK**  | Adversarial Tactics, Techniques, and Common Knowledge (framework de MITRE) |
| **C4**      | Context, Containers, Components, Code — modelo de arquitectura de software |
| **HPR**     | Holistic Project Radar (radar de 5 capas y 15 dimensiones para evaluación de proyectos) |
| **TC**      | Test Case (Caso de Prueba) — identificador de tests E2E (TC-01 a TC-33) |
| **PDCA**    | Plan-Do-Check-Act (ciclo de mejora continua)      |
| **TCO**     | Total Cost of Ownership (Costo Total de Propiedad) |
| **NLP**     | Natural Language Processing (Procesamiento de Lenguaje Natural) |
| **ML**      | Machine Learning (Aprendizaje Automático)        |
| **AI**      | Artificial Intelligence (Inteligencia Artificial) |
| **APT**     | Advanced Persistent Threat (Amenaza Persistente Avanzada) |
| **Tenzir**  | Plataforma de análisis de datos de red (pipeline de eventos) |
| **OpenSearch** | Motor de búsqueda y análisis open source (fork de Elasticsearch) |
| **MFA**     | Multi-Factor Authentication                     |
| **SSO**     | Single Sign-On                                  |
| **OIDC**    | OpenID Connect                                  |
| **OTP**     | One-Time Password                               |
| **TOTP**    | Time-based One-Time Password                    |
| **RBAC**    | Role-Based Access Control                       |
| **WAF**     | Web Application Firewall                        |
| **HSM**     | Hardware Security Module                        |
| **CA**      | Certificate Authority                           |
| **DMZ**     | Demilitarized Zone                              |
| **CORS**    | Cross-Origin Resource Sharing (Intercambio de Recursos de Origen Cruzado) — configurado en la API de FastAPI y Nginx |
| **IaC**     | Infraestructura como Código (Infrastructure as Code) — Docker Compose, Dockerfiles y scripts del repositorio |
| **YAML**    | YAML Ain't Markup Language                      |
| **HTML**    | HyperText Markup Language                       |
| **CSS**     | Cascading Style Sheets                          |
| **JS**      | JavaScript                                      |
| **WebSocket** | Protocolo de comunicación bidireccional en tiempo real |

## Abreviaturas de Herramientas y Plataformas

| Abreviatura         | Término Completo                                        |
|---------------------|---------------------------------------------------------|
| **TheHive**         | Plataforma de gestión de casos e incidentes             |
| **Cortex**          | Motor de análisis de amenazas e IoCs                    |
| **Shuffle**         | Plataforma de orquestación SOAR                         |
| **MISP**            | Malware Information Sharing Platform                    |
| **Elasticsearch**   | Motor de búsqueda y análisis                            |
| **Redis**           | Sistema de caché y broker de mensajes                   |
| **Grafana**         | Plataforma de visualización de métricas                 |
| **Loki**            | Sistema de agregación de logs                           |
| **Promtail**        | Agente de recolección de logs                           |
| **Nginx**           | Servidor web y proxy inverso                            |
| **MariaDB**         | Sistema de gestión de bases de datos                    |
| **PostgreSQL**      | Sistema de gestión de bases de datos                    |
| **Git**             | Sistema de control de versiones                         |
| **GitHub**          | Plataforma de alojamiento de código                     |
| **Docker Compose**  | Herramienta de orquestación de contenedores             |
| **PowerShell**      | Shell de línea de comandos de Windows                   |
| **Bash**            | Shell de línea de comandos de Unix/Linux                |
| **Python**          | Lenguaje de programación                                |
| **Pytest**          | Framework de testing para Python                        |
| **FastAPI**         | Framework web para Python                               |

## Abreviaturas de Seguridad y Threat Intelligence

| Abreviatura      | Término Completo                                      |
|------------------|-------------------------------------------------------|
| **MITRE ATT&CK** | Adversarial Tactics, Techniques, and Common Knowledge |
| **CISA**         | Cybersecurity and Infrastructure Security Agency      |
| **TLP**          | Traffic Light Protocol                                |
| **CVE**          | Common Vulnerabilities and Exposures                  |
| **CVSS**         | Common Vulnerability Scoring System                   |
| **XSS**          | Cross-Site Scripting                                  |
| **CSRF**         | Cross-Site Request Forgery                            |

## Abreviaturas Académicas y de Investigación

| Abreviatura | Término Completo                                    |
|-------------|-----------------------------------------------------|
| **DOI**     | Digital Object Identifier                           |
| **IEEE**    | Institute of Electrical and Electronics Engineers   |
| **ACM**     | Association for Computing Machinery                 |
| **IJCRT**   | International Journal of Creative Research Thoughts |

## Términos relacionados con testing

- **Collección/collected**: casos de prueba encontrados por `pytest` durante la fase de recolección.
- **Deselected**: casos excluidos por marcadores (`-m`) o filtros.
- **Selected**: casos que finalmente se ejecutarán.
- **Skipped**: casos omitidos en runtime mediante `pytest.skip` (por ejemplo, falta de dependencia externa).
- **Xfail**: caso marcado como fallo esperado; no se usa masivamente en este repositorio, pero puede aparecer en pruebas experimentales.
- **Smoke test**: prueba rápida post-despliegue para verificar que el stack está operativo.
- **Atomic test**: prueba aislada de un componente o escenario con dependencias mínimas.

## Términos relacionados con métricas

- **Observada**: valor real obtenido de las ejecuciones del workflow y almacenado en `soar-metrics`.
- **Objetivo**: valor deseado o umbral de mejora continua definido por el equipo.
- **Umbral (`threshold_p50`, `threshold_p90`)**: valor límite que una métrica observada no debería superar.
- **Cobertura (`coverage`)**: porcentaje de código fuente ejecutado por los tests.

## Uso en documentación

- Al usar un acrónimo por primera vez en un documento, escribir la expansión completa seguida del acrónimo entre paréntesis.
- No emplear acrónimos en títulos de sección sin haberlos definido previamente en el documento.
- Mantener este glosario actualizado cuando se introduzcan nuevos términos técnicos.
