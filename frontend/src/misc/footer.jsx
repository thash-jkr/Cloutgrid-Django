import {
  faFacebook,
  faInstagram,
  faXTwitter,
  faYoutube,
} from "@fortawesome/free-brands-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import React from "react";
import { Link } from "react-router-dom";

const Footer = () => {
  return (
    <div className="px-3">
      <footer className="container mx-auto flex flex-wrap justify-center content-center mb-8 border-t w-full">
        <div className="px-2 py-3 flex flex-col justify-center content-center items-center w-full">
          <div className="flex justify-between content-center py-5 w-2/3 md:w-3/5 lg:w-1/5 text-3xl">
            <a href="https://facebook.com/cloutgrid" className="transition-all duration-500 hover:scale-110 hover:text-orange-500">
              <FontAwesomeIcon icon={faFacebook} />
            </a>
            <a href="https://instagram.com/cloutgrid" className="transition-all duration-500 hover:scale-110 hover:text-orange-500">
              <FontAwesomeIcon icon={faInstagram} />
            </a>
            <a href="https://youtube.com/cloutgrid" className="transition-all duration-500 hover:scale-110 hover:text-orange-500">
              <FontAwesomeIcon icon={faYoutube} />
            </a>
            <a href="https://x.com/cloutgrid" className="transition-all duration-500 hover:scale-110 hover:text-orange-500">
              <FontAwesomeIcon icon={faXTwitter} />
            </a>
          </div>

          <div className="flex justify-center content-center font-bold text-lg md:w-3/4 py-5">
            <ul className="flex flex-col md:flex-row justify-around content-center text-center w-full">
              <li className="transition-all duration-500 hover:scale-110 hover:text-orange-500">
                <a href="mailto:info@cloutgrid.com">Contact us</a>
              </li>
              {/* <li>
              <a href="/">Our Services</a>
            </li> */}
              <li className="transition-all duration-500 hover:scale-110 hover:text-orange-500">
                <Link to={"/privacypolicy"}>Privacy Policy</Link>
              </li>

              <li className="transition-all duration-500 hover:scale-110 hover:text-orange-500">
                <Link to={"/eula"}>Terms of Service</Link>
              </li>

              <li className="transition-all duration-500 hover:scale-110 hover:text-orange-500">
                <Link to={"/data-deletion"}>Data Deletion</Link>
              </li>

              {/* <li>
              <a href="/">Careers</a>
            </li> */}
            </ul>
          </div>

          <div className="flex flex-col justify-center content-center text-center py-5">
            <p>Cloutgrid Copyright © 2025 Cloutgrid - All rights reserved</p>
            <p className="font-bold transition-all duration-500 hover:scale-110 hover:text-orange-500">
              Designed By: <a href="https://thash.me">@thash</a>
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Footer;
