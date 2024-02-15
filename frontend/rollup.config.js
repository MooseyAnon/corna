/* Simple RollupJS config for bundling the Corna frontend.
*
* To support as many browsers as possible we want to bundle our
* code to both ES5 and ES6.
*/

// most of this comes from here: https://shorturl.at/auABK
import { nodeResolve } from '@rollup/plugin-node-resolve';
import { getBabelOutputPlugin } from '@rollup/plugin-babel';
import commonjs from '@rollup/plugin-commonjs';
import terser from '@rollup/plugin-terser';

let terserConf = terser(
    {
      ecma: 2015,
      mangle: { toplevel: true },
      compress: {
        module: true,
        toplevel: true,
        unsafe_arrows: true
      },
      output: { quote_style: 1 }
  }
)


function rollupConf(filename) {
    /* Automatically generate the rollup config object. */

    const input = `./public/scripts/${filename}.js`;
    const es5Out = `./public/scripts/${filename}-es5.js`
    const es6Out = `./public/scripts/${filename}-es6.js`

    return { 
        input: input,
        output: [
            {  
                file: es6Out,
                format: 'es',
            },
            {
                file: es5Out,
                format: "cjs",
                plugins: [
                    getBabelOutputPlugin({
                        presets: ['@babel/preset-env'],
                    }),
                    terserConf,
                    
                ]
            }
        ],
        plugins: [
                nodeResolve({
                    browser: true
                }),
                commonjs(),
                terserConf,
            ],
        onwarn: function(warning, handler) {

            if (warning.code === "THIS_IS_UNDEFINED") { return; }
            /*
            * running bable on the output causes the following -:
            *     "Mixing named and default exports"
            * It seems to be caused by running the commonjs plugin
            * on the input files first. I dont really know why this is
            * but will silence it for now till I figure out how to
            * fix it.
            */
            if (warning.code === "MIXED_EXPORTS") { return; }

            handler(warning);
        }
    }
}

// Add any new files to be bundled here
// note the lack of '.js' extension
// that is on purpose!
const files = [
    "createButton",
    "editor",
    "login",
    "signup",
];
export default files.map((file)=> rollupConf(file));
