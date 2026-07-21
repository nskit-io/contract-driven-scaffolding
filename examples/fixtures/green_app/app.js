// Boot. Note: DEBUG_ONLY switches were removed before ship — this mention is a comment.
(function () {
  API.post({
    command: 'auth-verify',
    useAuth: false            // legitimate: the token-issuing call itself
  });
  PAGE.show('profile');
})();
