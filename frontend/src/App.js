import React, { useEffect, useState } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { useDispatch } from "react-redux";
import { setCredentials } from "./slices/authSlice";
import axios from "axios";

import Home from "./components/home";
import Login from "./components/authentication/login";
import Logout from "./components/authentication/logout";
import Register from "./components/authentication/register";
import Profile from "./components/profile/profile";
import Profiles from "./components/profile/profiles";
import CreatorUserRegisterForm from "./components/authentication/registerCreator";
import BusinessUserRegisterForm from "./components/authentication/registerBusiness";
import JobList from "./components/jobs/jobList";
import MyJobs from "./components/jobs/myJobs";
import PasswordResetRequest from "./components/authentication/password_reset/passwordReset";
import PasswordResetConfirm from "./components/authentication/password_reset/confirmReset";
import PrivacyPolicy from "./misc/privacyPolicy";
import EULA from "./misc/agreement";
import ProtectedRoute from "./navigation/ProtectedRoute";
import PublicRoute from "./navigation/PublicRoute";

import "./App.css";
import NotFound from "./navigation/NotFound";
import DeleteAccount from "./privacy/deleteAccount";
import DataDeletionPolicy from "./misc/DataDeletion";

function App() {
  const dispatch = useDispatch();
  const [hydrate, setHydrate] = useState(false);

  useEffect(() => {
    const access = localStorage.getItem("access");
    const refresh = localStorage.getItem("refresh");
    const type = localStorage.getItem("type");
    const user = localStorage.getItem("user");

    if (access && refresh && type && user) {
      const userObj = JSON.parse(user);
      dispatch(setCredentials({ access, refresh, type, user: userObj }));
    }

    setHydrate(true);
  }, [dispatch]);

  if (!hydrate) {
    return <div className="loading">Loading...</div>;
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/privacypolicy" element={<PrivacyPolicy />} />
        <Route path="/eula" element={<EULA />} />
        <Route path="/data-deletion" element={<DataDeletionPolicy />} />

        <Route element={<PublicRoute />}>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route
            path="/register/creator"
            element={<CreatorUserRegisterForm />}
          />
          <Route
            path="/register/business"
            element={<BusinessUserRegisterForm />}
          />
          <Route path="/forgot-password" element={<PasswordResetRequest />} />
          <Route
            path="/reset-password/:uid/:token"
            element={<PasswordResetConfirm />}
          />
        </Route>

        <Route element={<ProtectedRoute />}>
          <Route path="/profile" element={<Profile />} />
          <Route path="/profiles/:username" element={<Profiles />} />
          <Route path="/logout" element={<Logout />} />
          <Route path="/privacy/account/delete" element={<DeleteAccount />} />
        </Route>

        <Route element={<ProtectedRoute allowedType="creator" />}>
          <Route path="/jobs" element={<JobList />} />
        </Route>

        <Route element={<ProtectedRoute allowedType="business" />}>
          <Route path="/my-jobs" element={<MyJobs />} />
        </Route>

        <Route path="*" element={<NotFound />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
