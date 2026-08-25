import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import homeCCC from "../assets/home_ccc.png";
import homeCreator from "../assets/—Pngtree—blogger review concept vetor creative_7689749.png";
import creatorCore from "../assets/creator_core.png";
import collabCore from "../assets/collaboration_core.png";
import iOSLogo from "../assets/app_store_logo.png";
import androidLogo from "../assets/play_store_logo.png";
import selection from "../assets/selecting_creators.png";
import "animate.css";
import NavBar from "../common/navBar";
import Feed from "./feed/feed";
import BreatheAnimation from "../misc/breathe";
import { useSelector } from "react-redux";
import Footer from "../misc/footer";

const LoggedOutHome = () => {
  return (
    <div className="bg-white">
      <div className="container mx-auto flex flex-col justify-center content-center">
        <NavBar />

        <div className="flex h-svh">
          <div className="center-vertical lg:w-1/2">
            <div className="center-vertical">
              <div className="hidden lg:flex">
                <BreatheAnimation />
              </div>

              <div className="flex lg:hidden justify-center items-center w-full mb-5">
                <img
                  src={homeCreator}
                  alt="Home Right"
                  className="w-3/4 h-auto"
                />
              </div>

              <div className="flex lg:hidden font-mono">
                <h1>Create • Connect • Collaborate</h1>
              </div>

              <div className="flex flex-col justify-center items-center my-5">
                <p className=" w-3/4 text-blue-900 text-sm font-bold text-justify">
                  Are you a visionary creator ready to showcase your talents and
                  land exciting projects? Or a business seeking innovative ideas
                  to elevate your brand? You’re in the right place!
                </p>
              </div>

              <div className="flex w-3/4 lg:w-1/2 mb-5">
                <a
                  className="w-1/2 h-auto hover:scale-105 transition-all duration-500 cursor-pointer"
                  href="https://apps.apple.com/in/app/cloutgrid/id6745302913"
                >
                  <img src={iOSLogo} />
                </a>

                <a
                  className="w-1/2 h-auto hover:scale-105 transition-all duration-500 cursor-pointer"
                  href="https://play.google.com/store/apps/details?id=com.cloutgrid.androidapp"
                >
                  <img src={androidLogo} />
                </a>
              </div>

              {/* <Link to="/register">
                <button className="button-54">Get Started</button>
              </Link> */}
            </div>
          </div>

          <div className="hidden lg:flex justify-center items-center w-1/2 animate__animated animate__fadeInRight">
            <img src={homeCreator} alt="Home Right" className="w-3/4 h-auto" />
          </div>
        </div>

        <div className="flex flex-col lg:flex-row my-16 lg:my-32">
          <div className="flex justify-center items-center w-full mb-16 lg:mb-0">
            <img src={creatorCore} alt="Home Right" className="w-full h-auto" />
          </div>

          <div className="center-vertical">
            <div className="center-vertical">
              <h1 className="font-extrabold text-2xl lg:text-4xl text-orange-500">
                For Creator
              </h1>
              <div className="flex flex-col justify-center items-center my-5">
                <p className="text-sm lg:text-xl w-3/4 text-blue-900 font-semibold text-justify">
                  You’ve built your following—now it’s time to monetize it. With
                  Cloutgrid, discover businesses actively looking to collaborate
                  with creators like you. No algorithms, no guesswork. Just real
                  opportunities, curated for your niche.
                </p>
              </div>
              <Link to="/register/creator">
                <button className="button-54">Join as a Creator</button>
              </Link>
            </div>
          </div>
        </div>

        <div className="flex lg:hidden justify-center items-center w-full my-8">
          <img src={homeCCC} alt="Home Right" className="w-full h-auto" />
        </div>

        <div className="flex flex-col lg:flex-row my-16 lg:my-32">
          <div className="center-vertical">
            <div className="center-vertical">
              <h1 className="font-extrabold text-2xl lg:text-4xl text-orange-500">
                For Business
              </h1>
              <div className="flex flex-col justify-center items-center my-5">
                <p className="text-sm lg:text-xl w-3/4 text-blue-900 font-semibold text-justify">
                  Stop scrolling through endless profiles and cold emails.
                  Cloutgrid makes it simple for businesses to connect with the
                  perfect content creator—whether it’s for your next campaign,
                  product launch, or brand partnership. Post an opportunity and
                  let creators come to you.
                </p>
              </div>
              <Link to="/register/business">
                <button className="button-54">Join as a Business</button>
              </Link>
            </div>
          </div>

          <div className="hidden lg:flex justify-center items-center w-full mt-16 lg:mt-0">
            <img src={collabCore} alt="Home Right" className="w-full h-auto" />
          </div>
        </div>

        <div className="flex flex-col lg:flex-row my-16 lg:my-32">
          <div className="flex justify-center items-center w-full mb-16 lg:mb-0">
            <img src={selection} alt="Home Right" className="w-full h-auto" />
          </div>

          <div className="center-vertical">
            <div className="center-vertical">
              <h1 className="font-extrabold text-2xl lg:text-4xl text-orange-500">
                Join Cloutgrid Today
              </h1>
              <div className="flex flex-col justify-center items-center my-5">
                <p className="text-sm lg:text-xl w-3/4 text-blue-900 font-semibold text-justify">
                  It’s not just about being seen—it’s about being seen by the
                  right people. Cloutgrid helps businesses and creators team up
                  to reach target audiences with authentic, tailored content
                  that performs. Say goodbye to wasted reach and hello to
                  results.
                </p>
              </div>
              <Link to="/register">
                <button className="button-54">Join Now</button>
              </Link>
            </div>
          </div>
        </div>

        <Footer />
      </div>
    </div>
  );
};

const Home = () => {
  const [auth, setAuth] = useState(false);
  const access = useSelector((state) => state.auth.access);

  useEffect(() => {
    if (access) {
      setAuth(true);
    } else {
      setAuth(false);
    }
  }, [access]);

  return <>{auth ? <Feed /> : <LoggedOutHome />}</>;
};

export default Home;
