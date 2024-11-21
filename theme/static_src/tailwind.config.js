/**
 * This is a minimal config.
 *
 * If you need the full config, get it from here:
 * https://unpkg.com/browse/tailwindcss@latest/stubs/defaultConfig.stub.js
 */

module.exports = {
    content: [
        /**
         * HTML. Paths to Django template files that will contain Tailwind CSS classes.
         */

        /*  Templates within theme app (<tailwind_app_name>/templates), e.g. base.html. */
        '../templates/**/*.html',

        /*
         * Main templates directory of the project (BASE_DIR/templates).
         * Adjust the following line to match your project structure.
         */
        '../../templates/**/*.html',

        /*
         * Templates in other django apps (BASE_DIR/<any_app_name>/templates).
         * Adjust the following line to match your project structure.
         */
        '../../**/templates/**/*.html',

        /**
         * JS: If you use Tailwind CSS in JavaScript, uncomment the following lines and make sure
         * patterns match your project structure.
         */
        /* JS 1: Ignore any JavaScript in node_modules folder. */
        // '!../../**/node_modules',
        /* JS 2: Process all JavaScript files in the project. */
        //'../../**/*.js',

        /**
         * Python: If you use Tailwind CSS classes in Python, uncomment the following line
         * and make sure the pattern below matches your project structure.
         */
        '../../**/*.py',
    ],
    theme: {
        extend: {
          screens: {
            'xs': '470px',
            'custom_xl' : '1536px',
            'custom_xl_1' : '1325px',
            'custom_lg' : '1283px',
            'custom_lg_1' : '1242px',
            'custom_lg_2' : '1195px',
            'custom_lg_3' : '1092px',
            'custom_md' : '1009px',
            'custom_md_1' : '850px',
            'custom_md_2' : '760px',
            'custom_sm' : '544px',
          },
    
          colors: {
            redux: {
              green: '#41644A',
              lightgreen: '#81A969',
              lightgreen2: '#9fc588',
              tintwhite1: '#DDEEE7',
              tintwhite2: '#F6F6F6',
              gray: '#888',

              metal_bg: '#BCCDE6',
              metal_txt: '#4F5A6C',
              plastic_bg: '#A7CC90',
              plastic_bg_txt: '#41644A',
              glass_bg: '#D6BCE6',
              glass_txt: '#8F4D86',

            }
          },
    
          backgroundImage: theme => ({
            'gradient-to-b-redux': 'linear-gradient(to bottom, #41644A, #ffffff)',
          }),
    
          rotate: {
            'n20': '-17deg',
          },
    
          height: {
            'redux85':'85%',
            'redux75':'75%',
            'redux65':'65%',
            'redux55':'55%',
            'redux10':'10%',
          },
    
          width: {
            'redux85':'85%',
            'redux75':'75%',
            'redux65':'65%',
            'redux55':'55%',
            'redux10':'10%',
          }
        },
      },
    plugins: [
        /**
         * '@tailwindcss/forms' is the forms plugin that provides a minimal styling
         * for forms. If you don't like it or have own styling for forms,
         * comment the line below to disable '@tailwindcss/forms'.
         */
        require('@tailwindcss/forms'),
        require('@tailwindcss/typography'),
        require('@tailwindcss/aspect-ratio'),
    ],
}
