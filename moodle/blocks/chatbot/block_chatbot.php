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

        // Pasar configuración al widget JS vía data attributes
        $backend_url = get_config('block_chatbot', 'backend_url');
        $api_token   = get_config('block_chatbot', 'api_token');
        $course_id   = (int)$COURSE->id;
        $page_type   = $PAGE->pagetype;

        $this->page->requires->js(new moodle_url('/blocks/chatbot/chat.js'));

        $this->content->text = '<div id="chatbot-widget"
            data-backend-url="' . s($backend_url) . '"
            data-api-token="' . s($api_token) . '"
            data-role="' . s($role) . '"
            data-page="' . s($page_type) . '"
            data-course-id="' . $course_id . '"
            data-career="' . s($career) . '"
        ></div>';
        $this->content->footer = '';

        return $this->content;
    }

    public function applicable_formats() {
        return ['all' => true]; // Disponible en todas las páginas
    }
}
