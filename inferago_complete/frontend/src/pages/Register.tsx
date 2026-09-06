import { useState } from "react";
import { Link } from "react-router-dom";
import { useRegister } from "../hooks/useAuth";
import { Activity } from "lucide-react";

export default function Register() {
  const [fullName, setFullName] = useState("");
  const [email, setEmail]       = useState("");
  const [password, setPassword] = useState("");
  const mutation                 = useRegister();
  const errorMsg                 = (mutation.error as any)?.response?.data?.detail ?? "Registration failed";

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-950 px-4">
      <div className="w-full max-w-md">
        <div className="flex items-center justify-center gap-3 mb-8">
          <div className="bg-blue-600 p-2 rounded-lg"><Activity className="w-6 h-6 text-white" /></div>
          <div>
            <span className="text-2xl font-bold text-white">Inferago</span>
            <p className="text-xs text-gray-500">AI Workflow Monitor</p>
          </div>
        </div>
        <div className="card">
          <h1 className="text-xl font-bold text-white mb-1">Create account</h1>
          <p className="text-gray-400 text-sm mb-6">Start monitoring your AI workflows</p>
          <form onSubmit={(e) => { e.preventDefault(); mutation.mutate({ full_name: fullName, email, password }); }} className="space-y-4">
            <div>
              <label className="block text-sm text-gray-400 mb-1">Full name</label>
              <input type="text" value={fullName} onChange={(e) => setFullName(e.target.value)} placeholder="Your name" className="input" required />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Email</label>
              <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" className="input" required />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Password <span className="text-gray-600">(min 8 chars)</span></label>
              <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" className="input" required minLength={8} />
            </div>
            {mutation.isError && (
              <div className="bg-red-900/40 border border-red-700 rounded-lg px-4 py-3">
                <p className="text-red-300 text-sm">{errorMsg}</p>
              </div>
            )}
            <button type="submit" disabled={mutation.isPending} className="btn-primary w-full">
              {mutation.isPending ? "Creating account..." : "Create account"}
            </button>
          </form>
          <p className="text-center text-sm text-gray-500 mt-5">
            Already have an account? <Link to="/login" className="text-blue-400 hover:underline">Sign in</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
