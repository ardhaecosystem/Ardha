"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

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
    <div className="min-h-screen w-full relative bg-black overflow-hidden text-white selection:bg-primary/30">
      {/* Animated Aurora Burst Background */}
      <div
        className="absolute inset-0 z-0 transition-all duration-300 opacity-60"
        style={{
          background: `
            radial-gradient(ellipse 120% 80% at ${70 + mousePosition.x / 100}% ${20 + mousePosition.y / 100}%, rgba(124, 58, 237, 0.15), transparent 50%),
            radial-gradient(ellipse 100% 60% at ${30 + mousePosition.x / 150}% ${10 + mousePosition.y / 150}%, rgba(0, 255, 255, 0.12), transparent 60%),
            radial-gradient(ellipse 90% 70% at 50% 0%, rgba(138, 43, 226, 0.18), transparent 65%),
            radial-gradient(ellipse 110% 50% at ${80 + mousePosition.x / 200}% ${30 + mousePosition.y / 200}%, rgba(255, 215, 0, 0.08), transparent 40%),
            #000000
          `,
        }}
      />

      {/* Scanline Effect */}
      <div className="absolute inset-0 z-[1] pointer-events-none scanline opacity-20"></div>

      {/* Floating Particles */}
      <div className="absolute inset-0 z-0">
        {[...Array(30)].map((_, i) => (
          <div
            key={i}
            className="absolute w-1 h-1 bg-white/20 rounded-full animate-float-slow"
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
      <nav className="relative z-50 backdrop-blur-md bg-black/20 border-b border-white/5 sticky top-0">
        <div className="max-w-7xl mx-auto px-6 py-4 flex justify-between items-center">
          <div className="flex items-center gap-3 group cursor-pointer">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-purple-600 flex items-center justify-center shadow-[0_0_15px_rgba(124,58,237,0.5)] group-hover:shadow-[0_0_25px_rgba(124,58,237,0.8)] transition-all duration-300">
              <span className="text-white font-bold text-xl">A</span>
            </div>
            <span className="text-white font-bold text-xl tracking-tight group-hover:text-glow transition-all duration-300">
              Ardha
            </span>
          </div>
          <div className="flex items-center gap-4">
            <Link href="/login">
              <Button
                variant="ghost"
                className="text-white/80 hover:text-white hover:bg-white/10"
              >
                Login
              </Button>
            </Link>
            <Link href="/register">
              <Button variant="neon" className="rounded-xl">
                Get Started
              </Button>
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative z-10 max-w-7xl mx-auto px-6 pt-32 pb-32 flex flex-col items-center justify-center min-h-[80vh]">
        <div className="text-center max-w-5xl mx-auto">
          {/* Badge */}
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/5 backdrop-blur-md border border-white/10 mb-8 animate-fade-in hover:border-primary/50 transition-colors duration-300 cursor-default">
            <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse shadow-[0_0_10px_rgba(74,222,128,0.8)]"></span>
            <span className="text-white/80 text-sm font-medium tracking-wide">
              Open Source • AI-Native • Production Ready
            </span>
          </div>

          {/* Main Headline */}
          <h1
            className="text-7xl md:text-9xl font-bold text-white mb-8 tracking-tight leading-tight animate-fade-in-up"
            style={{
              textShadow: "0 0 40px rgba(124, 58, 237, 0.3)",
            }}
          >
            The Future of <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-white via-purple-200 to-purple-400 animate-pulse-glow">
              Project Management
            </span>
          </h1>

          {/* Subheadline */}
          <p
            className="text-xl md:text-2xl text-white/60 mb-12 max-w-3xl mx-auto leading-relaxed animate-fade-in-up"
            style={{ animationDelay: "0.1s" }}
          >
            The first truly{" "}
            <span className="text-primary font-semibold text-glow">
              AI-native platform
            </span>{" "}
            where artificial intelligence doesn't just assist—it{" "}
            <span className="text-white font-semibold text-glow">
              collaborates
            </span>{" "}
            with your team to build software faster.
          </p>

          {/* CTA Buttons */}
          <div
            className="flex flex-col sm:flex-row gap-6 justify-center items-center animate-fade-in-up"
            style={{ animationDelay: "0.2s" }}
          >
            <Button
              onClick={() => router.push("/register")}
              size="lg"
              className="text-lg px-10 py-6 rounded-2xl bg-primary hover:bg-primary/90 shadow-[0_0_30px_rgba(124,58,237,0.4)] hover:shadow-[0_0_50px_rgba(124,58,237,0.6)] hover:scale-105 transition-all duration-300"
            >
              Start Building Free
            </Button>
            <Button
              variant="outline"
              size="lg"
              onClick={() => {
                document
                  .getElementById("features")
                  ?.scrollIntoView({ behavior: "smooth" });
              }}
              className="text-lg px-10 py-6 rounded-2xl border-white/20 bg-white/5 hover:bg-white/10 hover:border-white/40 backdrop-blur-md text-white"
            >
              Explore Features
            </Button>
          </div>

          {/* Stats */}
          <div
            className="mt-24 grid grid-cols-3 gap-12 max-w-3xl mx-auto animate-fade-in-up"
            style={{ animationDelay: "0.3s" }}
          >
            {[
              { value: "78+", label: "API Endpoints" },
              { value: "400+", label: "AI Models" },
              { value: "100%", label: "Open Source" },
            ].map((stat, i) => (
              <div key={i} className="text-center group">
                <div className="text-5xl font-bold text-white mb-2 group-hover:text-primary transition-colors duration-300 text-glow">
                  {stat.value}
                </div>
                <div className="text-white/40 text-sm font-medium uppercase tracking-wider">
                  {stat.label}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section
        id="features"
        className="relative z-10 max-w-7xl mx-auto px-6 py-32"
      >
        <div className="text-center mb-20">
          <h2 className="text-5xl md:text-6xl font-bold text-white mb-6 text-glow">
            Built for the AI Era
          </h2>
          <p className="text-xl text-white/50 max-w-2xl mx-auto">
            Not a traditional PM tool with AI bolted on. A completely reimagined
            platform designed for AI-first workflows.
          </p>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
          {features.map((feature, index) => (
            <Card
              key={index}
              className="group relative overflow-hidden border-white/10 bg-white/5 hover:bg-white/10 transition-all duration-500 hover:-translate-y-2"
            >
              <div className="absolute inset-0 bg-gradient-to-br from-primary/20 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />

              <div className="relative p-8 h-full flex flex-col">
                <div className="text-6xl mb-6 transform group-hover:scale-110 transition-transform duration-500 filter drop-shadow-[0_0_15px_rgba(255,255,255,0.3)]">
                  {feature.icon}
                </div>

                <h3 className="text-2xl font-bold text-white mb-4 group-hover:text-primary transition-colors duration-300">
                  {feature.title}
                </h3>

                <p className="text-white/60 leading-relaxed text-lg">
                  {feature.description}
                </p>
              </div>
            </Card>
          ))}
        </div>
      </section>

      {/* Tech Stack Section */}
      <section className="relative z-10 max-w-7xl mx-auto px-6 py-32">
        <div className="glass-panel rounded-3xl p-16 relative overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-r from-primary/10 via-transparent to-primary/10 opacity-50" />

          <div className="relative z-10">
            <div className="text-center mb-16">
              <h2 className="text-4xl font-bold text-white mb-4 text-glow">
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
                <div
                  key={index}
                  className="text-center group cursor-pointer p-4 rounded-2xl hover:bg-white/5 transition-all duration-300"
                >
                  <div className="w-20 h-20 mx-auto mb-4 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center group-hover:bg-primary/20 group-hover:border-primary/50 group-hover:scale-110 group-hover:shadow-[0_0_20px_rgba(124,58,237,0.3)] transition-all duration-300">
                    <span className="text-3xl">⚡</span>
                  </div>
                  <div className="text-white font-bold text-lg mb-1 group-hover:text-primary transition-colors">
                    {tech.name}
                  </div>
                  <div className="text-white/40 text-sm">{tech.desc}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section className="relative z-10 max-w-5xl mx-auto px-6 py-32 text-center">
        <div className="relative group">
          <div className="absolute inset-0 bg-gradient-to-r from-primary via-purple-500 to-pink-500 rounded-3xl blur-3xl opacity-20 group-hover:opacity-40 transition-opacity duration-500" />

          <div className="relative glass-panel rounded-3xl p-16 border-white/20">
            <h2 className="text-5xl md:text-7xl font-bold text-white mb-8 text-glow">
              Ready to Build the Future?
            </h2>
            <p className="text-xl text-white/70 mb-12 max-w-2xl mx-auto">
              Join the AI-native revolution. Start managing projects the way
              they should be managed—with intelligence.
            </p>
            <Button
              onClick={() => router.push("/register")}
              size="lg"
              className="text-xl px-12 py-8 rounded-2xl bg-white text-black hover:bg-white/90 hover:scale-105 shadow-[0_0_40px_rgba(255,255,255,0.3)] transition-all duration-300 font-bold"
            >
              Get Started Free →
            </Button>
            <p className="text-white/40 text-sm mt-8 font-medium tracking-wide">
              NO CREDIT CARD REQUIRED • OPEN SOURCE • DEPLOY ANYWHERE
            </p>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="relative z-10 border-t border-white/10 bg-black/40 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto px-6 py-12">
          <div className="flex flex-col md:flex-row justify-between items-center gap-6">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary to-purple-600 flex items-center justify-center shadow-lg">
                <span className="text-white font-bold text-sm">A</span>
              </div>
              <span className="text-white/60 font-medium">
                © 2024 Ardha. Built with ❤️ for the future.
              </span>
            </div>
            <div className="flex gap-8 text-white/60 font-medium">
              <a
                href="https://github.com/yourusername/ardha"
                className="hover:text-primary hover:text-glow transition-all duration-300"
              >
                GitHub
              </a>
              <a
                href="/docs"
                className="hover:text-primary hover:text-glow transition-all duration-300"
              >
                Docs
              </a>
              <a
                href="/blog"
                className="hover:text-primary hover:text-glow transition-all duration-300"
              >
                Blog
              </a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
