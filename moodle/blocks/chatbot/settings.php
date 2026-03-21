<?php
defined('MOODLE_INTERNAL') || die();

if ($ADMIN->fulltree) {
    $settings->add(new admin_setting_configtext(
        'block_chatbot/backend_url',
        'URL del backend',
        'Ejemplo: https://chatbot.miinstituto.edu/api',
        '',
        PARAM_URL
    ));

    $settings->add(new admin_setting_configtext(
        'block_chatbot/api_token',
        'Token de autenticación',
        'Token secreto para autenticar con el backend',
        '',
        PARAM_RAW
    ));
}
