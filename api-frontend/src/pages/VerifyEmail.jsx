import { useEffect, useState } from "react";

export default function VerifyEmail({ backendUrl, token }) {
  const [status, setStatus] = useState("pending");

  useEffect(() => {
    const verify = async () => {
      try {
        const res = await fetch(`${backendUrl}/verify?token=${token}`);
        if (res.ok) setStatus("success");
        else setStatus("error");
      } catch {
        setStatus("error");
      }
    };
    verify();
  }, [backendUrl, token]);

  return (
    <div className="app-viewport">
      <div className="card center column">
        {status === "pending" && <p className="h2">Verifying...</p>}
        {status === "success" && (
          <div className="message success">Your email has been verified!</div>
        )}
        {status === "error" && (
          <div className="message error">Verification failed.</div>
        )}
        <a className="btn-link" href="/login">Back to Login</a>
      </div>
    </div>
  );
}
