"use client";

import { useEffect, useState } from "react";
import { authApi } from "./api";
import { isLoggedIn } from "./auth";
import type { UserResponse } from "./types";

export function useCurrentUser() {
  const [user, setUser] = useState<UserResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isLoggedIn()) {
      setLoading(false);
      return;
    }
    authApi
      .me()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
  }, []);

  return { user, loading };
}
