keycloak-v2-purple-theme (ready-to-deploy)
-----------------------------------------

Что внутри:
- themes/keycloak-v2-purple-theme/login/theme.properties
- login/resources/css/login.css
- login/resources/css/styles.css
- login/templates/footer.ftl

Эта тема **расширяет `keycloak.v2`** и изменяет только фон (фиолетный градиент) и пару косметических деталей,
чтобы минимально воздействовать на существующие шаблоны и поведение.

Установка:
1) Распакуйте папку в директорию `$KEYCLOAK_HOME/themes/` (или смонтируйте в контейнере в `/opt/keycloak/themes/`).
2) Перезапустите Keycloak (или запустите с отключённым кешем тем при разработке):
   bin/kc.sh start --spi-theme--static-max-age=-1 --spi-theme--cache-themes=false --spi-theme--cache-templates=false
3) В админке Realm → Realm Settings → Themes → Login Theme выберите `keycloak-v2-purple-theme` и сохраните.
4) Откройте страницу логина (например, URL авторизации вашего клиента).

ВАЖНО:
- Если вы используете Keycloak в контейнере, не забудьте скопировать/смонтировать тему в образ/контейнер (иначе сервер не увидит файлы).
- Начиная с некоторых версий, части `keycloak.v2` (особенно Account/Admin) используют React и могут вести себя иначе при расширении.
  Однако для классической страницы логина этот метод хорошо работает (см. README и документацию Keycloak).

Если захотите, могу создать также вариант, который просто модифицирует существующую директорию `keycloak.v2/login` (patch),
или подготовить инструкции для Dockerfile/Helm/Kubernetes монтирования — скажите, какой у вас сценарий развертывания.
