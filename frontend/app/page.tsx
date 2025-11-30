"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

export default function LandingPage() {
  const router = useRouter();
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });
  const [scrollY, setScrollY] = useState(0);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      setMousePosition({ x: e.clientX, y: e.clientY });
    };

    const handleScroll = () => {
      setScrollY(window.scrollY);
    };

    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("scroll", handleScroll);

    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("scroll", handleScroll);
    };
  }, []);

  const features = [
    {
      icon: "🤖",
      title: "AI-Native Architecture",
      description:
        "Built from the ground up with AI at its core. Not just a chatbot - AI that understands your entire project context.",
    },
    {
      icon: "⚡",
      title: "Lightning Fast",
      description:
        "Real-time collaboration with WebSocket streaming. See changes as they happen, powered by modern infrastructure.",
    },
    {
      icon: "🎯",
      title: "Smart Workflows",
      description:
        "LangGraph-powered workflows that adapt to your team. AI agents that learn from your patterns and optimize processes.",
    },
    {
      icon: "🔗",
      title: "GitHub Integration",
      description:
        "Deep GitHub integration with webhooks, PR analysis, and automated code review. Your code and tasks, unified.",
    },
    {
      icon: "💎",
      title: "Notion-Style Databases",
      description:
        "Flexible databases with 11+ property types. Organize projects your way, powered by intelligent data relationships.",
    },
    {
      icon: "🧠",
      title: "Vector Memory",
      description:
        "AI with long-term memory. Every conversation, every decision - stored in semantic vectors for intelligent recall.",
    },
  ];

  return (
    <div className="min-h-screen w-full relative bg-black overflow-hidden">
      {/* Animated Aurora Burst Background */}
      <div
        className="absolute inset-0 z-0 transition-all duration-300"
        style={{
          background: `
            radial-gradient(ellipse 120% 80% at ${70 + mousePosition.x / 100}% ${20 + mousePosition.y / 100}%, rgba(255, 20, 147, 0.15), transparent 50%),
            radial-gradient(ellipse 100% 60% at ${30 + mousePosition.x / 150}% ${10 + mousePosition.y / 150}%, rgba(0, 255, 255, 0.12), transparent 60%),
            radial-gradient(ellipse 90% 70% at 50% 0%, rgba(138, 43, 226, 0.18), transparent 65%),
            radial-gradient(ellipse 110% 50% at ${80 + mousePosition.x / 200}% ${30 + mousePosition.y / 200}%, rgba(255, 215, 0, 0.08), transparent 40%),
            #000000
          `,
        }}
      />

      {/* Floating Particles */}
      <div className="absolute inset-0 z-0">
        {[...Array(20)].map((_, i) => (
          <div
            key={i}
            className="absolute w-1 h-1 bg-white/20 rounded-full animate-float"
            style={{
              left: `${Math.random() * 100}%`,
              top: `${Math.random() * 100}%`,
              animationDelay: `${Math.random() * 5}s`,
              animationDuration: `${10 + Math.random() * 20}s`,
            }}
          />
        ))}
      </div>

      {/* Navigation */}
      <nav className="relative z-20 backdrop-blur-md bg-white/5 border-b border-white/10">
        <div className="max-w-7xl mx-auto px-6 py-4 flex justify-between items-center">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center">
              <span className="text-white font-bold text-lg">A</span>
            </div>
            <span className="text-white font-bold text-xl">Ardha</span>
          </div>
          <div className="flex items-center gap-4">
            <Link
              href="/login"
              className="px-4 py-2 text-white/80 hover:text-white transition-colors"
            >
              Login
            </Link>
            <Link
              href="/register"
              className="px-6 py-2 rounded-xl bg-gradient-to-r from-purple-600 to-pink-600 text-white font-semibold hover:from-purple-700 hover:to-pink-700 transition-all duration-200 shadow-lg shadow-purple-500/25"
            >
              Get Started
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative z-10 max-w-7xl mx-auto px-6 pt-20 pb-32">
        <div className="text-center">
          {/* Badge */}
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/10 backdrop-blur-sm border border-white/20 mb-8 animate-fade-in">
            <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></span>
            <span className="text-white/80 text-sm">
              Open Source • AI-Native • Production Ready
            </span>
          </div>

          {/* Main Headline */}
          <h1
            className="text-6xl md:text-8xl font-bold text-white mb-6 animate-fade-in-up"
            style={{
              background: "linear-gradient(to right, #fff, #a78bfa, #ec4899)",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
              backgroundClip: "text",
            }}
          >
            The Future of
            <br />
            Project Management
          </h1>

          {/* Subheadline */}
          <p
            className="text-xl md:text-2xl text-white/60 mb-12 max-w-3xl mx-auto animate-fade-in-up"
            style={{ animationDelay: "0.1s" }}
          >
            The first truly{" "}
            <span className="text-purple-400 font-semibold">
              AI-native platform
            </span>{" "}
            where artificial intelligence doesn't just assist—it{" "}
            <span className="text-pink-400 font-semibold">collaborates</span>{" "}
            with your team.
          </p>

          {/* CTA Buttons */}
          <div
            className="flex flex-col sm:flex-row gap-4 justify-center items-center animate-fade-in-up"
            style={{ animationDelay: "0.2s" }}
          >
            <button
              onClick={() => router.push("/register")}
              className="px-8 py-4 rounded-xl bg-gradient-to-r from-purple-600 to-pink-600 text-white font-semibold text-lg hover:from-purple-700 hover:to-pink-700 transition-all duration-200 shadow-2xl shadow-purple-500/50 hover:shadow-purple-500/75 hover:scale-105"
            >
              Start Building Free
            </button>
            <button
              onClick={() => {
                document
                  .getElementById("features")
                  ?.scrollIntoView({ behavior: "smooth" });
              }}
              className="px-8 py-4 rounded-xl bg-white/10 backdrop-blur-sm border border-white/20 text-white font-semibold text-lg hover:bg-white/20 transition-all duration-200"
            >
              Explore Features
            </button>
          </div>

          {/* Stats */}
          <div
            className="mt-20 grid grid-cols-3 gap-8 max-w-2xl mx-auto animate-fade-in-up"
            style={{ animationDelay: "0.3s" }}
          >
            <div className="text-center">
              <div className="text-4xl font-bold text-white mb-2">78+</div>
              <div className="text-white/60 text-sm">API Endpoints</div>
            </div>
            <div className="text-center">
              <div className="text-4xl font-bold text-white mb-2">400+</div>
              <div className="text-white/60 text-sm">AI Models</div>
            </div>
            <div className="text-center">
              <div className="text-4xl font-bold text-white mb-2">100%</div>
              <div className="text-white/60 text-sm">Open Source</div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section
        id="features"
        className="relative z-10 max-w-7xl mx-auto px-6 py-20"
      >
        <div className="text-center mb-16">
          <h2 className="text-4xl md:text-5xl font-bold text-white mb-4">
            Built for the AI Era
          </h2>
          <p className="text-xl text-white/60 max-w-2xl mx-auto">
            Not a traditional PM tool with AI bolted on. A completely reimagined
            platform designed for AI-first workflows.
          </p>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((feature, index) => (
            <div
              key={index}
              className="group relative"
              style={{
                animation: "fade-in-up 0.6s ease-out",
                animationDelay: `${index * 0.1}s`,
                animationFillMode: "both",
              }}
            >
              {/* Glow Effect */}
              <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-purple-500/20 to-pink-500/20 blur-xl opacity-0 group-hover:opacity-100 transition-opacity duration-300" />

              {/* Card */}
              <div className="relative backdrop-blur-xl bg-white/5 rounded-2xl border border-white/10 p-8 hover:bg-white/10 hover:border-white/20 transition-all duration-300 h-full">
                {/* Icon */}
                <div className="text-5xl mb-4 transform group-hover:scale-110 transition-transform duration-300">
                  {feature.icon}
                </div>

                {/* Title */}
                <h3 className="text-xl font-bold text-white mb-3">
                  {feature.title}
                </h3>

                {/* Description */}
                <p className="text-white/60 leading-relaxed">
                  {feature.description}
                </p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Tech Stack Section */}
      <section className="relative z-10 max-w-7xl mx-auto px-6 py-20">
        <div className="backdrop-blur-xl bg-white/5 rounded-3xl border border-white/10 p-12">
          <div className="text-center mb-12">
            <h2 className="text-4xl font-bold text-white mb-4">
              Production-Grade Stack
            </h2>
            <p className="text-white/60 text-lg">
              Built with modern, battle-tested technologies for enterprise
              reliability
            </p>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            {[
              { name: "FastAPI", desc: "Python Backend" },
              { name: "Next.js 15", desc: "React Framework" },
              { name: "PostgreSQL", desc: "Primary Database" },
              { name: "Redis", desc: "Caching Layer" },
              { name: "Qdrant", desc: "Vector Search" },
              { name: "LangGraph", desc: "AI Workflows" },
              { name: "Docker", desc: "Containerization" },
              { name: "OpenRouter", desc: "400+ AI Models" },
            ].map((tech, index) => (
              <div key={index} className="text-center group cursor-pointer">
                <div className="w-16 h-16 mx-auto mb-3 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center group-hover:bg-white/10 group-hover:scale-110 transition-all duration-300">
                  <span className="text-2xl">⚡</span>
                </div>
                <div className="text-white font-semibold mb-1">{tech.name}</div>
                <div className="text-white/40 text-sm">{tech.desc}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section className="relative z-10 max-w-4xl mx-auto px-6 py-20">
        <div className="relative">
          {/* Glow */}
          <div className="absolute inset-0 rounded-3xl bg-gradient-to-br from-purple-500/30 to-pink-500/30 blur-2xl" />

          {/* Card */}
          <div className="relative backdrop-blur-xl bg-white/10 rounded-3xl border border-white/20 p-12 text-center">
            <h2 className="text-4xl md:text-5xl font-bold text-white mb-6">
              Ready to Build the Future?
            </h2>
            <p className="text-xl text-white/60 mb-8 max-w-2xl mx-auto">
              Join the AI-native revolution. Start managing projects the way
              they should be managed—with intelligence.
            </p>
            <button
              onClick={() => router.push("/register")}
              className="px-10 py-5 rounded-xl bg-gradient-to-r from-purple-600 to-pink-600 text-white font-semibold text-lg hover:from-purple-700 hover:to-pink-700 transition-all duration-200 shadow-2xl shadow-purple-500/50 hover:shadow-purple-500/75 hover:scale-105"
            >
              Get Started Free →
            </button>
            <p className="text-white/40 text-sm mt-6">
              No credit card required • Open source • Deploy anywhere
            </p>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="relative z-10 border-t border-white/10 mt-20">
        <div className="max-w-7xl mx-auto px-6 py-12">
          <div className="flex flex-col md:flex-row justify-between items-center gap-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center">
                <span className="text-white font-bold text-lg">A</span>
              </div>
              <span className="text-white/60">
                © 2024 Ardha. Built with ❤️ for the future.
              </span>
            </div>
            <div className="flex gap-6 text-white/60">
              <a
                href="https://github.com/yourusername/ardha"
                className="hover:text-white transition-colors"
              >
                GitHub
              </a>
              <a href="/docs" className="hover:text-white transition-colors">
                Docs
              </a>
              <a href="/blog" className="hover:text-white transition-colors">
                Blog
              </a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
