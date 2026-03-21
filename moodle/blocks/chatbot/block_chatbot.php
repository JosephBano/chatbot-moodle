<?php
defined('MOODLE_INTERNAL') || die();

class block_chatbot extends block_base {

    public function init() {
        $this->title = get_string('pluginname', 'block_chatbot');
    }

    public function get_content() {
        global $USER, $COURSE, $PAGE, $DB;

        if ($this->content !== null) {
            return $this->content;
        }

        $this->content = new stdClass();

        // Obtener rol del usuario en el curso actual
        $context = context_course::instance($COURSE->id);
        $roles   = get_user_roles($context, $USER->id);
        $role    = !empty($roles) ? reset($roles)->shortname : 'student';

        // Obtener carrera del perfil del usuario (campo personalizado 'carrera')
        $career = '';
        $field  = $DB->get_record('user_info_field', ['shortname' => 'carrera']);
        if ($field) {
            $data   = $DB->get_record('user_info_data', ['userid' => $USER->id, 'fieldid' => $field->id]);
            $career = $data ? $data->data : '';
        }

        // Pasar datos al widget JS — incluye course_id y career para el control de acceso
        $this->page->requires->js_call_amd('block_chatbot/chat', 'init', [
            get_config('block_chatbot', 'backend_url'),
            get_config('block_chatbot', 'api_token'),
            $role,
            $PAGE->pagetype,
            (int)$COURSE->id,
            $career
        ]);

        $this->content->text   = '<div id="chatbot-widget"></div>';
        $this->content->footer = '';

        return $this->content;
    }

    public function applicable_formats() {
        return ['all' => true]; // Disponible en todas las páginas
    }
}
