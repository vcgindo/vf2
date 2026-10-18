/* Build-resource settings only; application source and runtime behavior are unchanged.
DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
*/
'use strict';
const assert = require('assert');
process.env.NODE_ENV = 'production';
process.env.BABEL_ENV = 'production';
const checkerPath = require.resolve('/app/node_modules/react-dev-utils/ForkTsCheckerWebpackPlugin');
const OriginalChecker = require(checkerPath);
class BoundedChecker extends OriginalChecker {
  constructor(options = {}) {
    super({...options, typescript: {...options.typescript, memoryLimit: 1024}});
  }
}
require.cache[checkerPath].exports = BoundedChecker;
const configPath = require.resolve('/app/node_modules/react-scripts/config/webpack.config.js');
const factory = require(configPath);
require.cache[configPath].exports = environment => {
  const config = factory(environment);
  config.parallelism = 2;
  for (const plugin of config.optimization.minimizer || []) {
    if (plugin.options && 'parallel' in plugin.options) plugin.options.parallel = false;
  }
  assert((config.plugins || []).some(plugin =>
    plugin.constructor?.name === 'ForkTsCheckerWarningWebpackPlugin' || plugin.options?.typescript),
    'Existing TypeScript checker must remain enabled');
  return config;
};
require('/app/node_modules/react-scripts/scripts/build.js');
