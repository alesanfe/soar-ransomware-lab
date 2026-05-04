# Checklist de Seguridad (EDT 4.2)

> Este documento proporciona un checklist completo de seguridad para el laboratorio SOAR, asegurando que el entorno sea seguro y cumpla con las mejores prácticas de ciberseguridad.

## Tabla de Contenidos

1. [Seguridad de Red](#seguridad-de-red)
2. [Seguridad de Autenticación](#seguridad-de-autenticación)
3. [Seguridad de Datos](#seguridad-de-datos)
4. [Seguridad de Contenedores](#seguridad-de-contenedores)
5. [Seguridad de Aplicaciones](#seguridad-de-aplicaciones)
6. [Seguridad Operacional](#seguridad-operacional)
7. [Auditoría y Cumplimiento](#auditoría-y-cumplimiento)

---

## Seguridad de Red

### ✅ Configuración de Redes Docker

- [ ] **Red interna aislada**: `soar_net` configurada como `internal: true`
- [ ] **Red edge con puertos mínimos**: Solo puertos necesarios expuestos
- [ ] **Sin exposición de Elasticsearch**: Puerto 9200 solo accesible internamente
- [ ] **Firewall host configurado**: Restringir acceso a puertos de gestión
- [ ] **VPN para acceso remoto**: Acceso solo mediante VPN en producción

### ✅ Gestión de Puertos

| Puerto | Servicio | Exposición | Requiere Firewall |
|--------|----------|------------|-------------------|
| 9000 | TheHive | Edge | Sí |
| 9001 | Cortex | Edge | Sí |
| 3001 | Shuffle UI | Edge | Sí |
| 5001 | Shuffle API | Edge | Sí |
| 19200 | Elasticsearch | Edge (solo para debug) | Sí |

### ✅ Configuración TLS

- [ ] **TLS habilitado por defecto**: `ENABLE_TLS=true` en .env
- [ ] **Certificados autofirmados generados**: Ejecutar `./scripts/gen_certs.sh`
- [ ] **Rutas de certificados configuradas**: `TLS_CERT_PATH` y `TLS_KEY_PATH`
- [ ] **Rotación de certificados**: Anual o cuando expiren
- [ ] **Validación de certificados**: Habilitar en producción con CA real

---

## Seguridad de Autenticación

### ✅ Gestión de Credenciales

- [ ] **Sin credenciales por defecto**: Cambiar todos los valores `ChangeMe!`
- [ ] **Contraseñas fuertes**: Mínimo 12 caracteres, mayúsculas, minúsculas, números, símbolos
- [ ] **API keys únicas**: Generar con `openssl rand -hex 32`
- [ ] **Tokens webhook seguros**: Mínimo 32 caracteres alfanuméricos
- [ ] **Rotación de credenciales**: Cada 90 días

### ✅ Variables de Entorno

- [ ] **.env en .gitignore**: Archivo no versionado
- [ ] **Permisos restrictivos en .env**: `chmod 600 docker/.env`
- [ ] **Sin hardcodeo en scripts**: Usar variables de entorno
- [ ] **Secretos en vault**: Usar HashiCorp Vault o similar en producción

### ✅ Configuración de Servicios

**TheHive:**
- [ ] Cambiar contraseña admin por defecto
- [ ] Configurar autenticación LDAP/AD (opcional)
- [ ] Habilitar 2FA si está disponible
- [ ] API key rotada regularmente

**Cortex:**
- [ ] Secret key configurada en `cortex.application.conf`
- [ ] API key única generada
- [ ] Analyzers con credenciales seguras
- [ ] Rate limiting configurado

**Shuffle:**
- [ ] Contraseña admin cambiada
- [ ] API key por defecto cambiada
- [ ] Webhook tokens únicos
- [ ] Apps con credenciales seguras

---

## Seguridad de Datos

### ✅ Almacenamiento

- [ ] **Volúmenes Docker cifrados**: Usar LUKS o similar en producción
- [ ] **Backups cifrados**: Backups encriptados con GPG
- [ ] **Retención de logs**: Rotación y archivado seguro
- [ ] **Datos sensibles en reposo**: Cifrado en disco

### ✅ Gestión de Logs

- [ ] **Log rotation configurada**: `max-size: 10m`, `max-file: 3`
- [ ] **Logs sensibles redactados**: Sin credenciales en logs
- [ ] **Archivado de logs**: Logs antiguos comprimidos y cifrados
- [ ] **Monitorización de logs**: Alertas para patrones sospechosos

### ✅ Backups

- [ ] **Backup automatizado**: Script de backup programado
- [ ] **Backup de configuración**: .env, certs, schemas
- [ ] **Backup de volúmenes**: es_data, thehive_files, cortex_data
- [ **Test de restore**: Verificar backups regularmente
- [ ] **Backups offsite**: Almacenamiento en ubicación remota

---

## Seguridad de Contenedores

### ✅ Configuración Docker

- [ ] **Docker socket read-only**: `/var/run/docker.sock:ro`
- [ ] **Límites de recursos**: CPU y memoria limitados
- [ ] **Contenedores no root**: Ejecutar como usuario no root cuando sea posible
- [ ] **Imágenes actualizadas**: Usar versiones fijas y actualizadas
- [ ] **Escaneo de vulnerabilidades**: Trivy o similar

### ✅ Docker Compose

- [ ] **Healthchecks configurados**: Todos los servicios con healthcheck
- [ ] **Restart policy**: `unless-stopped` configurado
- [ ] **Redes separadas**: Edge e internal
- [ ] **Volúmenes nombrados**: No bind mounts para datos sensibles
- [ ] **Logging configurado**: JSON driver con rotación

### ✅ Imágenes Docker

| Imagen | Versión | Estado | Notas |
|--------|---------|--------|-------|
| thehiveproject/thehive | 3.5.2-1 | ✅ Estable | Compatible con ES 7.x |
| thehiveproject/cortex | 3.1.0-1 | ✅ Estable | Compatible con TheHive 3.x |
| shuffler.io/frontend | 1.3.0 | ✅ Estable | Versión LTS |
| shuffler.io/shuffle | 1.3.0 | ✅ Estable | Versión LTS |
| elasticsearch | 7.17.17 | ✅ Estable | Última 7.x |

---

## Seguridad de Aplicaciones

### ✅ Validación de Inputs

- [ ] **Validación JSON Schema**: Alertas validadas contra schema
- [ ] **Sanitización de inputs**: Scripts validan parámetros
- [ ] **Protección contra inyección**: No concatenación de comandos
- [ ] **Validación de tipos**: Chequeo de tipos de datos

### ✅ Gestión de Errores

- [ ] **Sin exposición de stack traces**: Errores genéricos al usuario
- [ ] **Logging de errores**: Errores registrados con contexto
- [ ] **Alertas de errores**: Notificación de errores críticos
- [ ] **Manejo graceful**: Degradación controlada

### ✅ APIs

- [ ] **Rate limiting**: Limitar peticiones por IP
- [ ] **Autenticación requerida**: Todas las APIs protegidas
- [ ] **HTTPS obligatorio**: TLS en producción
- [ ] **CORS configurado**: Orígenes permitidos restringidos

---

## Seguridad Operacional

### ✅ Procedimientos de Despliegue

- [ ] **Review de código**: Pull requests revisados
- [ ] **CI/CD seguro**: Secrets en variables de entorno
- [ ] **Despliegue automatizado**: Sin intervención manual
- [ ] **Rollback automático**: Reversión en caso de fallo

### ✅ Monitorización

- [ ] **Monitorización de recursos**: CPU, memoria, disco
- [ ] **Alertas de seguridad**: Intentos de intrusión
- [ ] **Audit logging**: Accesos registrados
- [ ] **Dashboard de seguridad**: Visibilidad en tiempo real

### ✅ Mantenimiento

- [ ] **Actualizaciones regulares**: Parches de seguridad aplicados
- [ ] **Revisión de accesos**: Auditoría de permisos
- [ ] **Limpieza de recursos**: Volúmenes e imágenes no usadas
- [ ] **Documentación actualizada**: Procedimientos revisados

---

## Auditoría y Cumplimiento

### ✅ Auditoría

- [ ] **Logs de auditoría**: Accesos y cambios registrados
- [ ] **Revisiones periódicas**: Auditoría trimestral
- [ ] **Penetration testing**: Pruebas de seguridad anuales
- [ ] **Compliance checks**: Verificación de estándares

### ✅ Cumplimiento

- [ ] **GDPR**: Protección de datos personales
- [ ] **ISO 27001**: Gestión de seguridad (si aplica)
- [ ] **NIST**: Framework de ciberseguridad
- [ ] **Políticas internas**: Cumplimiento de políticas empresa

---

## Checklist de Implementación

### Pre-Despliegue

- [ ] Ejecutar `./scripts/gen_certs.sh`
- [ ] Copiar `docker/.env.example` a `docker/.env`
- [ ] Cambiar todas las credenciales por defecto
- [ ] Configurar firewall host
- [ ] Verificar permisos de archivos
- [ ] Ejecutar script de verificación de dependencias

### Post-Despliegue

- [ ] Verificar healthchecks de todos los servicios
- [ ] Probar autenticación en TheHive, Cortex, Shuffle
- [ ] Verificar TLS en endpoints
- [ ] Configurar backups automatizados
- [ ] Establecer monitorización
- [ ] Documentar procedimientos de emergencia

### Mantenimiento

- [ ] **Diario**: Verificar estado de contenedores
- [ ] **Semanal**: Revisar logs de errores
- [ ] **Mensual**: Rotar credenciales
- [ ] **Trimestral**: Actualizar imágenes Docker
- [ ] **Anual**: Penetration testing

---

## Recursos Adicionales

### Herramientas de Seguridad

- **Trivy**: Escaneo de vulnerabilidades en contenedores
- **Docker Bench**: Seguridad de configuración Docker
- **Lynis**: Auditoría de seguridad del sistema
- **Fail2ban**: Protección contra ataques de fuerza bruta

### Documentación de Referencia

- [Docker Security Best Practices](https://docs.docker.com/engine/security/)
- [CIS Docker Benchmark](https://www.cisecurity.org/benchmark/docker)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)

---

**Última actualización**: 2025-05-03  
**Versión**: 1.0  
**Responsable**: Equipo de Seguridad
