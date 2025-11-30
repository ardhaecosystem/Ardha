"use client";

import { useState } from "react";
import { useAuthStore } from "@/lib/auth-store";

export default function SettingsPage() {
  const { user } = useAuthStore();
  const [isSaving, setIsSaving] = useState(false);
  const [successMessage, setSuccessMessage] = useState("");

  // Form state
  const [fullName, setFullName] = useState(user?.full_name || "");
  const [emailNotifications, setEmailNotifications] = useState(true);
  const [desktopNotifications, setDesktopNotifications] = useState(false);

  const handleSave = async () => {
    setIsSaving(true);
    // Simulate API call
    await new Promise((resolve) => setTimeout(resolve, 1000));
    setIsSaving(false);
    setSuccessMessage("Settings saved successfully!");
    setTimeout(() => setSuccessMessage(""), 3000);
  };

  return (
    <div className="max-w-4xl mx-auto px-6 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-white mb-2">Settings</h1>
        <p className="text-white/60 text-lg">
          Manage your account settings and preferences
        </p>
      </div>

      {/* Success Message */}
      {successMessage && (
        <div className="mb-6 backdrop-blur-xl bg-green-500/10 border border-green-500/20 rounded-xl p-4 flex items-center gap-3 animate-fade-in">
          <svg
            className="w-5 h-5 text-green-400 flex-shrink-0"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <span className="text-green-400">{successMessage}</span>
        </div>
      )}

      {/* Profile Section */}
      <div className="backdrop-blur-xl bg-white/5 rounded-2xl border border-white/10 p-8 mb-6">
        <h2 className="text-2xl font-bold text-white mb-6">Profile</h2>

        <div className="space-y-6">
          {/* Avatar */}
          <div className="flex items-center gap-6">
            <div className="w-20 h-20 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center text-white text-3xl font-bold">
              {user?.full_name?.charAt(0).toUpperCase() || "U"}
            </div>
            <div>
              <button className="px-4 py-2 rounded-lg bg-white/10 text-white hover:bg-white/20 transition-all duration-200 text-sm font-medium">
                Change Avatar
              </button>
              <p className="text-white/40 text-xs mt-2">
                JPG, GIF or PNG. Max size of 2MB.
              </p>
            </div>
          </div>

          {/* Full Name */}
          <div>
            <label className="block text-white/80 text-sm font-medium mb-2">
              Full Name
            </label>
            <input
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className="w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-purple-500/50 focus:border-transparent transition-all duration-200"
            />
          </div>

          {/* Email (Read-only) */}
          <div>
            <label className="block text-white/80 text-sm font-medium mb-2">
              Email Address
            </label>
            <input
              type="email"
              value={user?.email || ""}
              disabled
              className="w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white/60 cursor-not-allowed"
            />
            <p className="text-white/40 text-xs mt-2">
              Email cannot be changed. Contact support if needed.
            </p>
          </div>

          {/* Username (Read-only) */}
          <div>
            <label className="block text-white/80 text-sm font-medium mb-2">
              Username
            </label>
            <input
              type="text"
              value={user?.username || ""}
              disabled
              className="w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white/60 cursor-not-allowed"
            />
          </div>
        </div>
      </div>

      {/* Account Section */}
      <div className="backdrop-blur-xl bg-white/5 rounded-2xl border border-white/10 p-8 mb-6">
        <h2 className="text-2xl font-bold text-white mb-6">Account</h2>

        <div className="space-y-4">
          {/* Password */}
          <div className="flex items-center justify-between p-4 rounded-xl bg-white/5 border border-white/10">
            <div>
              <div className="text-white font-medium mb-1">Password</div>
              <div className="text-white/60 text-sm">
                Last changed 30 days ago
              </div>
            </div>
            <button className="px-4 py-2 rounded-lg bg-white/10 text-white hover:bg-white/20 transition-all duration-200 text-sm font-medium">
              Change
            </button>
          </div>

          {/* Connected Accounts */}
          <div className="p-4 rounded-xl bg-white/5 border border-white/10">
            <div className="text-white font-medium mb-4">
              Connected Accounts
            </div>
            <div className="space-y-3">
              {/* GitHub */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-white/10 flex items-center justify-center">
                    <svg
                      className="w-5 h-5 text-white"
                      fill="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        fillRule="evenodd"
                        d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"
                        clipRule="evenodd"
                      />
                    </svg>
                  </div>
                  <div>
                    <div className="text-white text-sm font-medium">GitHub</div>
                    <div className="text-white/60 text-xs">Connected</div>
                  </div>
                </div>
                <button className="text-red-400 hover:text-red-300 text-sm font-medium transition-colors">
                  Disconnect
                </button>
              </div>

              {/* Google */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-white/10 flex items-center justify-center">
                    <svg className="w-5 h-5" viewBox="0 0 24 24">
                      <path
                        fill="#EA4335"
                        d="M5.26620003,9.76452941 C6.19878754,6.93863203 8.85444915,4.90909091 12,4.90909091 C13.6909091,4.90909091 15.2181818,5.50909091 16.4181818,6.49090909 L19.9090909,3 C17.7818182,1.14545455 15.0545455,0 12,0 C7.27006974,0 3.1977497,2.69829785 1.23999023,6.65002441 L5.26620003,9.76452941 Z"
                      />
                      <path
                        fill="#34A853"
                        d="M16.0407269,18.0125889 C14.9509167,18.7163016 13.5660892,19.0909091 12,19.0909091 C8.86648613,19.0909091 6.21911939,17.076871 5.27698177,14.2678769 L1.23746264,17.3349879 C3.19279051,21.2936293 7.26500293,24 12,24 C14.9328362,24 17.7353462,22.9573905 19.834192,20.9995801 L16.0407269,18.0125889 Z"
                      />
                      <path
                        fill="#4A90E2"
                        d="M19.834192,20.9995801 C22.0291676,18.9520994 23.4545455,15.903663 23.4545455,12 C23.4545455,11.2909091 23.3454545,10.5272727 23.1818182,9.81818182 L12,9.81818182 L12,14.4545455 L18.4363636,14.4545455 C18.1187732,16.013626 17.2662994,17.2212117 16.0407269,18.0125889 L19.834192,20.9995801 Z"
                      />
                      <path
                        fill="#FBBC05"
                        d="M5.27698177,14.2678769 C5.03832634,13.556323 4.90909091,12.7937589 4.90909091,12 C4.90909091,11.2182781 5.03443647,10.4668121 5.26620003,9.76452941 L1.23999023,6.65002441 C0.43658717,8.26043162 0,10.0753848 0,12 C0,13.9195484 0.444780743,15.7301709 1.23746264,17.3349879 L5.27698177,14.2678769 Z"
                      />
                    </svg>
                  </div>
                  <div>
                    <div className="text-white text-sm font-medium">Google</div>
                    <div className="text-white/60 text-xs">Connected</div>
                  </div>
                </div>
                <button className="text-red-400 hover:text-red-300 text-sm font-medium transition-colors">
                  Disconnect
                </button>
              </div>
            </div>
          </div>

          {/* Account Info */}
          <div className="p-4 rounded-xl bg-white/5 border border-white/10">
            <div className="text-white/60 text-sm">
              Account created on {new Date().toLocaleDateString()}
            </div>
          </div>
        </div>
      </div>

      {/* Preferences Section */}
      <div className="backdrop-blur-xl bg-white/5 rounded-2xl border border-white/10 p-8 mb-6">
        <h2 className="text-2xl font-bold text-white mb-6">Preferences</h2>

        <div className="space-y-4">
          {/* Email Notifications */}
          <div className="flex items-center justify-between p-4 rounded-xl bg-white/5 border border-white/10">
            <div>
              <div className="text-white font-medium mb-1">
                Email Notifications
              </div>
              <div className="text-white/60 text-sm">
                Receive email updates about your projects
              </div>
            </div>
            <button
              onClick={() => setEmailNotifications(!emailNotifications)}
              className={`relative w-14 h-7 rounded-full transition-all duration-200 ${
                emailNotifications ? "bg-purple-500" : "bg-white/20"
              }`}
            >
              <div
                className={`absolute top-1 left-1 w-5 h-5 rounded-full bg-white transition-transform duration-200 ${
                  emailNotifications ? "translate-x-7" : "translate-x-0"
                }`}
              />
            </button>
          </div>

          {/* Desktop Notifications */}
          <div className="flex items-center justify-between p-4 rounded-xl bg-white/5 border border-white/10">
            <div>
              <div className="text-white font-medium mb-1">
                Desktop Notifications
              </div>
              <div className="text-white/60 text-sm">
                Show desktop notifications for important updates
              </div>
            </div>
            <button
              onClick={() => setDesktopNotifications(!desktopNotifications)}
              className={`relative w-14 h-7 rounded-full transition-all duration-200 ${
                desktopNotifications ? "bg-purple-500" : "bg-white/20"
              }`}
            >
              <div
                className={`absolute top-1 left-1 w-5 h-5 rounded-full bg-white transition-transform duration-200 ${
                  desktopNotifications ? "translate-x-7" : "translate-x-0"
                }`}
              />
            </button>
          </div>
        </div>
      </div>

      {/* Danger Zone */}
      <div className="backdrop-blur-xl bg-red-500/10 rounded-2xl border border-red-500/20 p-8">
        <h2 className="text-2xl font-bold text-red-400 mb-4">Danger Zone</h2>
        <p className="text-white/60 mb-6">
          Once you delete your account, there is no going back. Please be
          certain.
        </p>
        <button className="px-6 py-3 rounded-xl bg-red-500/20 border border-red-500/30 text-red-400 font-semibold hover:bg-red-500/30 transition-all duration-200">
          Delete Account
        </button>
      </div>

      {/* Save Button */}
      <div className="mt-8 flex justify-end gap-4">
        <button className="px-6 py-3 rounded-xl bg-white/10 text-white hover:bg-white/20 transition-all duration-200 font-medium">
          Cancel
        </button>
        <button
          onClick={handleSave}
          disabled={isSaving}
          className="px-8 py-3 rounded-xl bg-gradient-to-r from-purple-600 to-pink-600 text-white font-semibold hover:from-purple-700 hover:to-pink-700 transition-all duration-200 shadow-lg shadow-purple-500/25 disabled:opacity-50"
        >
          {isSaving ? "Saving..." : "Save Changes"}
        </button>
      </div>
    </div>
  );
}
