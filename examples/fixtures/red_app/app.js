(function () {
  var flag = DEBUG_ONLY;        // shipped landmine — live code, not a comment
  API.post({
    command: 'get-profile',
    useAuth: false              // abuse: not a token-issuing call
  });
  PAGE.show('dashboard');       // uses PAGE, but no override shipped (see styles.css)
})();
