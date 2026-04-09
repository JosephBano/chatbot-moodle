FROM php:8.1-apache

# Dependencias del sistema
RUN apt-get update && apt-get install -y \
    libpng-dev libjpeg-dev libfreetype6-dev \
    libzip-dev libxml2-dev libicu-dev \
    libldap2-dev libpq-dev \
    unzip curl git cron \
    && rm -rf /var/lib/apt/lists/*

# Extensiones PHP requeridas por Moodle
RUN docker-php-ext-configure gd --with-freetype --with-jpeg \
    && docker-php-ext-install -j$(nproc) \
    gd zip xml intl soap opcache \
    pdo pdo_mysql mysqli \
    ldap exif

# Configuración PHP para Moodle
RUN echo "max_input_vars = 5000"        >> /usr/local/etc/php/conf.d/moodle.ini \
    && echo "post_max_size = 64M"       >> /usr/local/etc/php/conf.d/moodle.ini \
    && echo "upload_max_filesize = 64M" >> /usr/local/etc/php/conf.d/moodle.ini \
    && echo "memory_limit = 256M"       >> /usr/local/etc/php/conf.d/moodle.ini

# Descargar e instalar Moodle 4.2.10, puede funcionar en versiones superiores
RUN curl -L https://download.moodle.org/download.php/direct/stable42/moodle-4.2.10.zip \
    -o /tmp/moodle.zip \
    && unzip -q /tmp/moodle.zip -d /var/www/ \
    && rm /tmp/moodle.zip \
    && chown -R www-data:www-data /var/www/moodle

# Directorio de datos de Moodle (moodledata)
RUN mkdir -p /var/moodledata \
    && chown www-data:www-data /var/moodledata \
    && chmod 770 /var/moodledata

# Apache: apuntar DocumentRoot a /var/www/moodle
RUN sed -i 's|/var/www/html|/var/www/moodle|g' \
    /etc/apache2/sites-available/000-default.conf \
    && sed -i 's|/var/www/html|/var/www/moodle|g' \
    /etc/apache2/apache2.conf \
    && a2enmod rewrite

EXPOSE 80
