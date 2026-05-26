"use client";

import { FormEvent, useState } from "react";
import { getAuthToken, setAuthToken } from "@/lib/api-client";

export function AuthTokenForm() {
  const [token, setToken] = useState(() => getAuthToken());

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setAuthToken(token);
  }

  return (
    <form className="controls" onSubmit={handleSubmit}>
      <input
        aria-label="API key or bearer token"
        className="input"
        onChange={(event) => setToken(event.target.value)}
        placeholder="API key or bearer token"
        type="password"
        value={token}
      />
      <button className="button secondary" type="submit">
        Save auth
      </button>
    </form>
  );
}
